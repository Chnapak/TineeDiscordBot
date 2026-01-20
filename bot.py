import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
import yt_dlp as youtube_dl
import asyncio
import json
from asyncio import Lock

# KEYS
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

def resolve_ffmpeg_path():
    env_path = os.getenv("FFMPEG_PATH")
    if env_path:
        return env_path
    local_path = os.path.join(os.path.dirname(__file__), "ffmpeg", "bin", "ffmpeg.exe")
    if os.path.exists(local_path):
        return local_path
    return "ffmpeg"

FFMPEG_PATH = resolve_ffmpeg_path()
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS = "-vn"

user_chats = {}  # Pro uchovávání historie chatu
user_locks = {}  # Zámky pro uživatele
user_chats_lock = Lock()


if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not set up in the .env file")

# Setting up OpenAI API
openai.api_key = OPENAI_API_KEY

# Setting up Discord bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# BOT EVENTS
is_sleeping = False  # Global variable for bot state
disabled_commands = []  # List for disabled commands
song_queues = {}
last_song_titles = {}


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


def load_user_chats():
    global user_chats
    try:
        with open("user_chats.json", "r", encoding="utf-8") as file:
            user_chats = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        user_chats = {}

# Funkce pro uložení historie uživatelů
def save_user_chats_sync():
    with open("user_chats.json", "w", encoding="utf-8") as file:
        json.dump(user_chats, file)

async def save_user_chats():
    async with user_chats_lock:
        await asyncio.to_thread(save_user_chats_sync)

# Načti historii při spuštění
load_user_chats()

# Pomocná funkce pro zámek uživatele
async def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = Lock()
    return user_locks[user_id]

async def fetch_openai_response(messages):
    def _call_openai():
        return openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages
        )
    return await asyncio.to_thread(_call_openai)

@bot.event
async def on_message(message):
    global is_sleeping

    if is_sleeping or message.author.bot or not message.guild:
        return

    if "tinee" in message.content.lower():
        user_id = str(message.author.id)

        # Získat zámek pro uživatele
        user_lock = await get_user_lock(user_id)
        async with user_lock:
            if user_id not in user_chats:
                user_chats[user_id] = [
                    {"role": "system", "content": "Your name is Tinee, you use she/her pronouns. Keep your messages short to feel realistic."}
                ]

            # Přidání zprávy uživatele
            user_chats[user_id].append({"role": "user", "content": message.content})

            # Omezit velikost historie, ale zachovat system prompt
            max_messages = 100
            history = user_chats[user_id]
            if len(history) > max_messages:
                system_prompt = history[0] if history and history[0].get("role") == "system" else None
                recent = history[-(max_messages - 1):]
                if system_prompt and system_prompt not in recent:
                    history = [system_prompt] + recent
                else:
                    history = recent
                user_chats[user_id] = history

            if not OPENAI_API_KEY:
                await message.channel.send("Nemám přístup k OpenAI API, takže nemůžu odpovědět. Zkuste to prosím později!")
                return

            try:
                response = await fetch_openai_response(user_chats[user_id])
                bot_response = response.choices[0].message.content
                user_chats[user_id].append({"role": "assistant", "content": bot_response})
                await message.channel.send(bot_response)
            except Exception as e:
                print(f"OpenAI error: {e}")
                await message.channel.send("Something went wrong, try again later.")

            # Uložit historii po každé zprávě
            await save_user_chats()
    else:
        await bot.process_commands(message)


# Helper function to check if a command is disabled or bot is sleeping
async def check_command_blocked(interaction: discord.Interaction, allow_when_sleeping=False):
    global disabled_commands
    if interaction.command.name in disabled_commands:
        await interaction.response.send_message(f"The command `{interaction.command.name}` is currently disabled.", ephemeral=True)
        return True
    if is_sleeping and not allow_when_sleeping:
        await interaction.response.send_message("Tinee is asleep. Use /wake to wake her.", ephemeral=True)
        return True
    return False


# BOT COMMANDS
@bot.tree.command(name="greeting", description="Sends one back!")
async def greeting(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


@bot.tree.command(name="sleep", description="Tells Tinee to go to sleep.")
@app_commands.checks.has_permissions(administrator=True)
async def sleep(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    global is_sleeping
    is_sleeping = True
    await interaction.response.send_message("Tinee is now asleep. She won't respond to commands.", ephemeral=True)


@bot.tree.command(name="wake", description="Wakes Tinee up.")
@app_commands.checks.has_permissions(administrator=True)
async def wake(interaction: discord.Interaction):
    if await check_command_blocked(interaction, allow_when_sleeping=True):
        return
    global is_sleeping
    is_sleeping = False
    await interaction.response.send_message("Tinee is awake and ready to help!", ephemeral=True)


@bot.tree.command(name="join", description="Bot joins your current voice channel.")
async def join(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if not interaction.guild.voice_client:
            await channel.connect()
            await interaction.response.send_message(f"Joined {channel}")
        else:
            await interaction.response.send_message("I'm already connected to a voice channel.", ephemeral=True)
    else:
        await interaction.response.send_message("You need to be in a voice channel for me to join!", ephemeral=True)


@bot.tree.command(name="leave", description="Bot leaves the voice channel.")
async def leave(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    voice_client = interaction.guild.voice_client

    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel!")
    else:
        await interaction.response.send_message("I'm not connected to any voice channel!", ephemeral=True)


# Fronta skladeb (globalní proměnná)
def get_guild_queue(guild_id):
    if guild_id not in song_queues:
        song_queues[guild_id] = []
    return song_queues[guild_id]

YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
}

async def youtube_search(query):
    def _extract_info():
        with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
            return ydl.extract_info(f"ytsearch:{query}", download=False)
    return await asyncio.to_thread(_extract_info)

@bot.tree.command(name="play", description="Plays a song in the voice channel.")
async def play(interaction: discord.Interaction, search: str):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    # Zkontroluj, zda uživatel je v hlasovém kanálu
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel for me to join and play music!")
        return

    # Získání nebo připojení bota do hlasového kanálu
    voice_client = interaction.guild.voice_client
    if not voice_client or not voice_client.is_connected():
        channel = interaction.user.voice.channel
        await channel.connect()
        voice_client = interaction.guild.voice_client

    # Defer odpověď
    if not interaction.response.is_done():
        await interaction.response.defer()

    try:
        info = await youtube_search(search)
        entries = info.get("entries") if info else []
        if not entries:
            await interaction.followup.send("Couldn't find the song. Try a different search.")
            return
        url = entries[0].get("url")
        title = entries[0].get("title")
        if not url or not title:
            await interaction.followup.send("Couldn't find the song. Try a different search.")
            return
    except Exception:
        await interaction.followup.send("Couldn't find the song. Try a different search.")
        return

    # Přidání skladby do fronty
    queue = get_guild_queue(interaction.guild.id)
    queue.append((url, title))
    await interaction.followup.send(f"Added `{title}` to the queue!")

    # Pokud nic nehraje, spusť první skladbu z fronty
    if not voice_client.is_playing():
        await play_next_song(voice_client, interaction.channel, interaction.guild.id)

async def get_similar_song(last_song_title):
    try:
        info = await youtube_search(f"{last_song_title} similar songs")
        entries = info.get("entries") if info else []
        if not entries:
            return None, None
        similar_url = entries[0].get("url")
        similar_title = entries[0].get("title")
        return similar_url, similar_title
    except Exception as e:
        print(f"Error fetching similar song: {e}")
        return None, None


async def play_next_song(voice_client, channel, guild_id):
    if not voice_client or not voice_client.is_connected():
        return

    def after_playing(err):
        if err:
            print(f"Error after playing: {err}")
        # Použij bot.loop pro spuštění další skladby
        coro = play_next_song(voice_client, channel, guild_id)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Error in after_playing: {e}")

    queue = get_guild_queue(guild_id)
    if queue:
        url, title = queue.pop(0)
        last_song_titles[guild_id] = title
        audio_source = FFmpegPCMAudio(
            url,
            executable=FFMPEG_PATH,
            before_options=FFMPEG_BEFORE_OPTIONS,
            options=FFMPEG_OPTIONS
        )

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(audio_source, after=after_playing)
        await channel.send(f"Now playing: `{title}`")
    else:
        # Pokud je fronta prázdná, hledá podobnou skladbu
        await channel.send("Queue is empty. Searching for a similar song...")
        seed_title = last_song_titles.get(guild_id)
        if not seed_title:
            await channel.send("No previous song found. Add more songs to the queue!")
            return
        url, title = await get_similar_song(seed_title)
        if url and title:
            last_song_titles[guild_id] = title
            audio_source = FFmpegPCMAudio(
                url,
                executable=FFMPEG_PATH,
                before_options=FFMPEG_BEFORE_OPTIONS,
                options=FFMPEG_OPTIONS
            )
            voice_client.play(audio_source, after=after_playing)
            await channel.send(f"Now playing a recommended song: `{title}`")
        else:
            await channel.send("Couldn't find a similar song. Add more songs to the queue!")



@bot.tree.command(name="pause", description="Pauses the current song.")
async def pause(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("Playback paused.", ephemeral=True)
    else:
        await interaction.response.send_message("No song is currently playing.", ephemeral=True)


@bot.tree.command(name="resume", description="Resumes the paused song.")
async def resume(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("Playback resumed.", ephemeral=True)
    else:
        await interaction.response.send_message("No song is currently paused.", ephemeral=True)


@bot.tree.command(name="queue", description="Shows the current song queue.")
async def queue(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    queue = get_guild_queue(interaction.guild.id)
    if queue:
        queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (_, title) in enumerate(queue)])
        await interaction.response.send_message(f"Current Queue:\n{queue_list}", ephemeral=True)
    else:
        await interaction.response.send_message("The queue is empty.", ephemeral=True)

@bot.tree.command(name="skip", description="Skips the currently playing song.")
async def skip(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing():
        # Ukončení aktuálního přehrávání
        voice_client.stop()
        await interaction.response.send_message("Skipped the current song!")
    else:
        await interaction.response.send_message("No song is currently playing to skip.", ephemeral=True)

@bot.tree.command(name="disable_command", description="Disables a specific bot command.")
@app_commands.checks.has_permissions(administrator=True)
async def disable_command(interaction: discord.Interaction, command_name: str):
    global disabled_commands

    if await check_command_blocked(interaction):
        return
    if command_name in disabled_commands:
        await interaction.response.send_message(f"The command `{command_name}` is already disabled.", ephemeral=True)
    elif command_name in [cmd.name for cmd in bot.tree.get_commands()]:
        disabled_commands.append(command_name)
        await interaction.response.send_message(f"The command `{command_name}` has been disabled.", ephemeral=True)
    else:
        await interaction.response.send_message(f"The command `{command_name}` does not exist.", ephemeral=True)


@bot.tree.command(name="enable_command", description="Enables a previously disabled bot command.")
@app_commands.checks.has_permissions(administrator=True)
async def enable_command(interaction: discord.Interaction, command_name: str):
    global disabled_commands

    if await check_command_blocked(interaction):
        return
    if command_name in disabled_commands:
        disabled_commands.remove(command_name)
        await interaction.response.send_message(f"The command `{command_name}` has been enabled.", ephemeral=True)
    else:
        await interaction.response.send_message(f"The command `{command_name}` is not disabled or does not exist.", ephemeral=True)


# Error handler for admin-only commands
@sleep.error
@wake.error
async def admin_only_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

# Run the bot
bot.run(DISCORD_TOKEN)
