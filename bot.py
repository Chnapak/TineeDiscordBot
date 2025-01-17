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

user_chats = {}  # Pro uchovávání historie chatu
user_locks = {}  # Zámky pro uživatele


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
user_chats = {}  # For tracking user chats
disabled_commands = []  # List for disabled commands


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
        with open("user_chats.json", "r") as file:
            user_chats = json.load(file)
    except FileNotFoundError:
        user_chats = {}

# Funkce pro uložení historie uživatelů
def save_user_chats():
    with open("user_chats.json", "w") as file:
        json.dump(user_chats, file)

# Načti historii při spuštění
load_user_chats()

# Pomocná funkce pro zámek uživatele
async def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = Lock()
    return user_locks[user_id]

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

            # Omezit velikost historie
            max_messages = 100
            user_chats[user_id] = user_chats[user_id][-max_messages:]

            if not OPENAI_API_KEY:
                await message.channel.send("Nemám přístup k OpenAI API, takže nemůžu odpovědět. Zkuste to prosím později!")
                return

            try:
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=user_chats[user_id]
                )
                bot_response = response.choices[0].message.content
                user_chats[user_id].append({"role": "assistant", "content": bot_response})
                await message.channel.send(bot_response)
            except Exception as e:
                print(f"OpenAI error: {e}")
                await message.channel.send("Something went wrong, try again later.")

            # Uložit historii po každé zprávě
            save_user_chats()
    else:
        await bot.process_commands(message)


# Helper function to check if a command is disabled
async def check_command_disabled(interaction: discord.Interaction):
    global disabled_commands
    if interaction.command.name in disabled_commands:
        await interaction.response.send_message(f"The command `{interaction.command.name}` is currently disabled.", ephemeral=True)
        return True
    return False


# BOT COMMANDS
@bot.tree.command(name="greeting", description="Sends one back!")
async def greeting(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


@bot.tree.command(name="sleep", description="Tells Tinee to go to sleep.")
@app_commands.checks.has_permissions(administrator=True)
async def sleep(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return
    global is_sleeping
    is_sleeping = True
    await interaction.response.send_message("Tinee is now asleep. She won't respond to commands.", ephemeral=True)


@bot.tree.command(name="wake", description="Wakes Tinee up.")
@app_commands.checks.has_permissions(administrator=True)
async def wake(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return
    global is_sleeping
    is_sleeping = False
    await interaction.response.send_message("Tinee is awake and ready to help!", ephemeral=True)


@bot.tree.command(name="join", description="Bot joins your current voice channel.")
async def join(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
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
    if await check_command_disabled(interaction):
        return
    voice_client = interaction.guild.voice_client

    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel!")
    else:
        await interaction.response.send_message("I'm not connected to any voice channel!", ephemeral=True)


# Fronta skladeb (globalní proměnná)
song_queue = []

@bot.tree.command(name="play", description="Plays a song in the voice channel.")
async def play(interaction: discord.Interaction, search: str):
    if await check_command_disabled(interaction):
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

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }

    # Defer odpověď
    if not interaction.response.is_done():
        await interaction.response.defer()

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)
            url = info['entries'][0]['url']
            title = info['entries'][0]['title']
        except Exception as e:
            await interaction.followup.send("Couldn't find the song. Try a different search.")
            return

    # Přidání skladby do fronty
    song_queue.append((url, title))
    await interaction.followup.send(f"Added `{title}` to the queue!")

    # Pokud nic nehraje, spusť první skladbu z fronty
    if not voice_client.is_playing():
        await play_next_song(voice_client, interaction.channel)

async def get_similar_song(last_song_title):
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            # Vyhledání podobné skladby
            info = ydl.extract_info(f"ytsearch:{last_song_title} similar songs", download=False)
            similar_url = info['entries'][0]['url']
            similar_title = info['entries'][0]['title']
            return similar_url, similar_title
        except Exception as e:
            print(f"Error fetching similar song: {e}")
            return None, None


async def play_next_song(voice_client, channel):
    if song_queue:
        url, title = song_queue.pop(0)
        audio_source = FFmpegPCMAudio(url, executable="C:/Users/atlan/Desktop/bot/ffmpeg/bin/ffmpeg.exe")

        def after_playing(err):
            if err:
                print(f"Error after playing: {err}")
            # Použij bot.loop pro spuštění další skladby
            coro = play_next_song(voice_client, channel)
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error in after_playing: {e}")

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(audio_source, after=after_playing)
        await channel.send(f"Now playing: `{title}`")
    else:
        # Pokud je fronta prázdná, hledá podobnou skladbu
        await channel.send("Queue is empty. Searching for a similar song...")
        last_song_title = song_queue[-1][1] if song_queue else "popular music"
        url, title = await get_similar_song(last_song_title)
        if url and title:
            audio_source = FFmpegPCMAudio(url, executable="C:/Users/atlan/Desktop/bot/ffmpeg/bin/ffmpeg.exe")
            voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(voice_client, channel), bot.loop))
            await channel.send(f"Now playing a recommended song: `{title}`")
        else:
            await channel.send("Couldn't find a similar song. Add more songs to the queue!")



@bot.tree.command(name="pause", description="Pauses the current song.")
async def pause(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("Playback paused.", ephemeral=True)
    else:
        await interaction.response.send_message("No song is currently playing.", ephemeral=True)


@bot.tree.command(name="resume", description="Resumes the paused song.")
async def resume(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("Playback resumed.", ephemeral=True)
    else:
        await interaction.response.send_message("No song is currently paused.", ephemeral=True)


@bot.tree.command(name="queue", description="Shows the current song queue.")
async def queue(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return

    if song_queue:
        queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (_, title) in enumerate(song_queue)])
        await interaction.response.send_message(f"Current Queue:\n{queue_list}", ephemeral=True)
    else:
        await interaction.response.send_message("The queue is empty.", ephemeral=True)

@bot.tree.command(name="skip", description="Skips the currently playing song.")
async def skip(interaction: discord.Interaction):
    if await check_command_disabled(interaction):
        return

    voice_client = interaction.guild.voice_client

    if voice_client and voice_client.is_playing():
        # Ukončení aktuálního přehrávání
        voice_client.stop()
        await interaction.response.send_message("Skipped the current song!")
        
        # Spuštění další skladby, pokud existuje
        await play_next_song(voice_client, interaction.channel)
    else:
        await interaction.response.send_message("No song is currently playing to skip.", ephemeral=True)

@bot.tree.command(name="disable_command", description="Disables a specific bot command.")
@app_commands.checks.has_permissions(administrator=True)
async def disable_command(interaction: discord.Interaction, command_name: str):
    global disabled_commands

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