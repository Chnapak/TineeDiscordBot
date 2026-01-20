import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer
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
SYSTEM_PROMPT = "Your name is Tinee, you use she/her pronouns. Keep your messages short to feel realistic."
CONFIG_FILE = "guild_config.json"

def new_guild_config():
    return {
        "ai_enabled": True,
        "ai_trigger": "keyword",
        "ai_keyword": "tinee",
        "ai_channels": [],
        "autoplay": False,
        "volume": 100
    }

user_chats = {}  # Pro uchovávání historie chatu
user_locks = {}  # Zámky pro uživatele
user_chats_lock = Lock()
guild_configs = {}
guild_configs_lock = Lock()


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
sleeping_guilds = set()
disabled_commands_by_guild = {}
song_queues = {}
last_song_titles = {}
current_tracks = {}


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
            data = json.load(file)
        if isinstance(data, dict):
            if data and all(isinstance(v, list) for v in data.values()):
                user_chats = {"_legacy": data}
            else:
                user_chats = data
        else:
            user_chats = {}
    except (FileNotFoundError, json.JSONDecodeError):
        user_chats = {}

# Funkce pro uložení historie uživatelů
def save_user_chats_sync():
    with open("user_chats.json", "w", encoding="utf-8") as file:
        json.dump(user_chats, file)

async def save_user_chats():
    async with user_chats_lock:
        await asyncio.to_thread(save_user_chats_sync)

def load_guild_configs():
    global guild_configs
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            guild_configs = data
        else:
            guild_configs = {}
    except (FileNotFoundError, json.JSONDecodeError):
        guild_configs = {}

def save_guild_configs_sync():
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(guild_configs, file)

async def save_guild_configs():
    async with guild_configs_lock:
        await asyncio.to_thread(save_guild_configs_sync)

def normalize_guild_config(config):
    if not isinstance(config, dict):
        return new_guild_config()
    if "ai_enabled" not in config:
        config["ai_enabled"] = True
    if "ai_trigger" not in config:
        config["ai_trigger"] = "keyword"
    if "ai_keyword" not in config:
        config["ai_keyword"] = "tinee"
    if "ai_channels" not in config:
        config["ai_channels"] = []
    if "autoplay" not in config:
        config["autoplay"] = False
    if "volume" not in config:
        config["volume"] = 100

    config["ai_enabled"] = bool(config.get("ai_enabled"))
    trigger = str(config.get("ai_trigger", "keyword")).lower()
    if trigger not in ("keyword", "mention", "both"):
        trigger = "keyword"
    config["ai_trigger"] = trigger

    keyword = str(config.get("ai_keyword", "tinee")).strip()
    config["ai_keyword"] = keyword if keyword else "tinee"

    channels = config.get("ai_channels", [])
    if not isinstance(channels, list):
        channels = []
    normalized_channels = []
    for channel_id in channels:
        try:
            normalized_channels.append(int(channel_id))
        except (TypeError, ValueError):
            continue
    config["ai_channels"] = normalized_channels

    config["autoplay"] = bool(config.get("autoplay"))
    try:
        volume = int(config.get("volume", 100))
    except (TypeError, ValueError):
        volume = 100
    config["volume"] = max(0, min(200, volume))
    return config

def get_guild_config(guild_id):
    guild_key = str(guild_id)
    if guild_key not in guild_configs:
        guild_configs[guild_key] = new_guild_config()
    guild_configs[guild_key] = normalize_guild_config(guild_configs[guild_key])
    return guild_configs[guild_key]

def should_respond_to_message(message, config):
    if not config.get("ai_enabled", True):
        return False
    allowed_channels = config.get("ai_channels", [])
    if allowed_channels and message.channel.id not in allowed_channels:
        return False

    trigger = config.get("ai_trigger", "keyword")
    keyword = str(config.get("ai_keyword", "tinee")).lower()
    content = (message.content or "").lower()
    is_mentioned = bot.user in message.mentions if bot.user else False

    if trigger == "mention":
        return is_mentioned
    if trigger == "both":
        return (keyword and keyword in content) or is_mentioned
    return keyword and keyword in content

def is_guild_sleeping(guild_id):
    return guild_id in sleeping_guilds

def get_disabled_commands(guild_id):
    if guild_id not in disabled_commands_by_guild:
        disabled_commands_by_guild[guild_id] = set()
    return disabled_commands_by_guild[guild_id]

def get_or_create_user_history(guild_id, user_id):
    guild_key = str(guild_id)
    user_key = str(user_id)
    if guild_key not in user_chats:
        user_chats[guild_key] = {}
    guild_chats = user_chats[guild_key]
    if user_key not in guild_chats:
        legacy = user_chats.get("_legacy", {})
        if user_key in legacy:
            guild_chats[user_key] = legacy.pop(user_key)
            if not legacy:
                user_chats.pop("_legacy", None)
        else:
            guild_chats[user_key] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return guild_chats[user_key]

# Načti historii při spuštění
load_user_chats()
load_guild_configs()

# Pomocná funkce pro zámek uživatele
async def get_user_lock(guild_id, user_id):
    lock_key = f"{guild_id}:{user_id}"
    if lock_key not in user_locks:
        user_locks[lock_key] = Lock()
    return user_locks[lock_key]

async def fetch_openai_response(messages):
    def _call_openai():
        return openai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages
        )
    return await asyncio.to_thread(_call_openai)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return
    guild_id = message.guild.id
    if is_guild_sleeping(guild_id):
        return

    config = get_guild_config(guild_id)
    if not should_respond_to_message(message, config):
        await bot.process_commands(message)
        return

    user_id = message.author.id

    # Získat zámek pro uživatele
    user_lock = await get_user_lock(guild_id, user_id)
    async with user_lock:
        history = get_or_create_user_history(guild_id, user_id)

        # Přidání zprávy uživatele
        history.append({"role": "user", "content": message.content})

        # Omezit velikost historie, ale zachovat system prompt
        max_messages = 100
        if len(history) > max_messages:
            system_prompt = history[0] if history and history[0].get("role") == "system" else None
            recent = history[-(max_messages - 1):]
            if system_prompt and system_prompt not in recent:
                new_history = [system_prompt] + recent
            else:
                new_history = recent
            history.clear()
            history.extend(new_history)

        if not OPENAI_API_KEY:
            await message.channel.send("Nemám přístup k OpenAI API, takže nemůžu odpovědět. Zkuste to prosím později!")
            return

        try:
            response = await fetch_openai_response(history)
            bot_response = response.choices[0].message.content
            history.append({"role": "assistant", "content": bot_response})
            await message.channel.send(bot_response)
        except Exception as e:
            print(f"OpenAI error: {e}")
            await message.channel.send("Something went wrong, try again later.")

        # Uložit historii po každé zprávě
        await save_user_chats()


# Helper function to check if a command is disabled or bot is sleeping
async def check_command_blocked(interaction: discord.Interaction, allow_when_sleeping=False, require_guild=True):
    if require_guild and not interaction.guild:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return True
    if interaction.guild:
        guild_id = interaction.guild.id
        disabled_commands = get_disabled_commands(guild_id)
        if interaction.command and interaction.command.name in disabled_commands:
            await interaction.response.send_message(f"The command `{interaction.command.name}` is currently disabled.", ephemeral=True)
            return True
        if is_guild_sleeping(guild_id) and not allow_when_sleeping:
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
    sleeping_guilds.add(interaction.guild.id)
    await interaction.response.send_message("Tinee is now asleep. She won't respond to commands.", ephemeral=True)


@bot.tree.command(name="wake", description="Wakes Tinee up.")
@app_commands.checks.has_permissions(administrator=True)
async def wake(interaction: discord.Interaction):
    if await check_command_blocked(interaction, allow_when_sleeping=True):
        return
    sleeping_guilds.discard(interaction.guild.id)
    await interaction.response.send_message("Tinee is awake and ready to help!", ephemeral=True)

@bot.tree.command(name="config", description="Shows the current per-server configuration.")
@app_commands.checks.has_permissions(administrator=True)
async def config(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    channel_ids = config.get("ai_channels", [])
    if channel_ids:
        channel_labels = []
        for channel_id in channel_ids:
            channel = interaction.guild.get_channel(channel_id)
            channel_labels.append(channel.mention if channel else str(channel_id))
        channels_text = ", ".join(channel_labels)
    else:
        channels_text = "all channels"
    await interaction.response.send_message(
        "AI enabled: {enabled}\nAI trigger: {trigger}\nAI keyword: {keyword}\nAI channels: {channels}\nAutoplay: {autoplay}\nVolume: {volume}%".format(
            enabled=config.get("ai_enabled", True),
            trigger=config.get("ai_trigger", "keyword"),
            keyword=config.get("ai_keyword", "tinee"),
            channels=channels_text,
            autoplay=config.get("autoplay", False),
            volume=config.get("volume", 100)
        ),
        ephemeral=True
    )

@bot.tree.command(name="set_ai", description="Enable or disable AI replies on this server.")
@app_commands.checks.has_permissions(administrator=True)
async def set_ai(interaction: discord.Interaction, enabled: bool):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    config["ai_enabled"] = enabled
    await save_guild_configs()
    await interaction.response.send_message(
        f"AI replies are now {'enabled' if enabled else 'disabled'} for this server.",
        ephemeral=True
    )

@bot.tree.command(name="set_ai_trigger", description="Sets how AI replies are triggered.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.choices(mode=[
    app_commands.Choice(name="keyword", value="keyword"),
    app_commands.Choice(name="mention", value="mention"),
    app_commands.Choice(name="both", value="both")
])
async def set_ai_trigger(interaction: discord.Interaction, mode: app_commands.Choice[str], keyword: str = None):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    config["ai_trigger"] = mode.value
    if keyword is not None:
        keyword = keyword.strip()
        if keyword:
            config["ai_keyword"] = keyword
    await save_guild_configs()
    await interaction.response.send_message(
        f"AI trigger set to `{mode.value}`.",
        ephemeral=True
    )

@bot.tree.command(name="set_ai_keyword", description="Sets the keyword that triggers AI replies.")
@app_commands.checks.has_permissions(administrator=True)
async def set_ai_keyword(interaction: discord.Interaction, keyword: str):
    if await check_command_blocked(interaction):
        return
    keyword = keyword.strip()
    if not keyword:
        await interaction.response.send_message("Keyword cannot be empty.", ephemeral=True)
        return
    config = get_guild_config(interaction.guild.id)
    config["ai_keyword"] = keyword
    await save_guild_configs()
    await interaction.response.send_message(
        f"AI keyword set to `{keyword}`.",
        ephemeral=True
    )

@bot.tree.command(name="allow_ai_channel", description="Allow AI replies in a specific channel.")
@app_commands.checks.has_permissions(administrator=True)
async def allow_ai_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    channels = config.get("ai_channels", [])
    if not channels:
        channels = []
    if channel.id in channels:
        await interaction.response.send_message(f"{channel.mention} is already allowed.", ephemeral=True)
        return
    channels.append(channel.id)
    config["ai_channels"] = channels
    await save_guild_configs()
    await interaction.response.send_message(
        f"AI replies are now allowed in {channel.mention}.",
        ephemeral=True
    )

@bot.tree.command(name="block_ai_channel", description="Disallow AI replies in a specific channel.")
@app_commands.checks.has_permissions(administrator=True)
async def block_ai_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    channels = config.get("ai_channels", [])
    if not channels:
        await interaction.response.send_message("AI is allowed in all channels. Use /allow_ai_channel to set a whitelist first.", ephemeral=True)
        return
    if channel.id not in channels:
        await interaction.response.send_message(f"{channel.mention} is not in the allow list.", ephemeral=True)
        return
    channels.remove(channel.id)
    config["ai_channels"] = channels
    await save_guild_configs()
    await interaction.response.send_message(
        f"AI replies are now blocked in {channel.mention}.",
        ephemeral=True
    )

@bot.tree.command(name="clear_ai_channels", description="Allow AI replies in all channels.")
@app_commands.checks.has_permissions(administrator=True)
async def clear_ai_channels(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    config["ai_channels"] = []
    await save_guild_configs()
    await interaction.response.send_message(
        "AI replies are now allowed in all channels.",
        ephemeral=True
    )


@bot.tree.command(name="join", description="Bot joins your current voice channel.")
async def join(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
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
    voice_client = interaction.guild.voice_client

    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("Disconnected from the voice channel!")
    else:
        await interaction.response.send_message("I'm not connected to any voice channel!", ephemeral=True)


# Fronta skladeb (per-guild)
def get_guild_volume(guild_id):
    config = get_guild_config(guild_id)
    return config.get("volume", 100)

def build_audio_source(url, guild_id):
    volume = get_guild_volume(guild_id) / 100.0
    source = FFmpegPCMAudio(
        url,
        executable=FFMPEG_PATH,
        before_options=FFMPEG_BEFORE_OPTIONS,
        options=FFMPEG_OPTIONS
    )
    return PCMVolumeTransformer(source, volume=volume)

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
        current_tracks[guild_id] = {"title": title, "url": url}
        audio_source = build_audio_source(url, guild_id)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(audio_source, after=after_playing)
        await channel.send(f"Now playing: `{title}`")
    else:
        current_tracks.pop(guild_id, None)
        config = get_guild_config(guild_id)
        if not config.get("autoplay", False):
            await channel.send("Queue is empty. Add more songs to the queue!")
            return

        # Pokud je fronta prázdná, hledá podobnou skladbu
        await channel.send("Queue is empty. Searching for a similar song...")
        seed_title = last_song_titles.get(guild_id)
        if not seed_title:
            await channel.send("No previous song found. Add more songs to the queue!")
            return
        url, title = await get_similar_song(seed_title)
        if url and title:
            last_song_titles[guild_id] = title
            current_tracks[guild_id] = {"title": title, "url": url}
            audio_source = build_audio_source(url, guild_id)
            voice_client.play(audio_source, after=after_playing)
            await channel.send(f"Now playing a recommended song: `{title}`")
        else:
            await channel.send("Couldn't find a similar song. Add more songs to the queue!")



@bot.tree.command(name="pause", description="Pauses the current song.")
async def pause(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
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

    queue = get_guild_queue(interaction.guild.id)
    if queue:
        queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (_, title) in enumerate(queue)])
        await interaction.response.send_message(f"Current Queue:\n{queue_list}", ephemeral=True)
    else:
        await interaction.response.send_message("The queue is empty.", ephemeral=True)

@bot.tree.command(name="nowplaying", description="Shows the currently playing song.")
async def nowplaying(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return

    voice_client = interaction.guild.voice_client
    track = current_tracks.get(interaction.guild.id)
    if voice_client and track and (voice_client.is_playing() or voice_client.is_paused()):
        status = "Paused" if voice_client.is_paused() else "Now playing"
        await interaction.response.send_message(f"{status}: `{track['title']}`")
    else:
        await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

@bot.tree.command(name="volume", description="Sets playback volume (0-200).")
async def volume(interaction: discord.Interaction, level: int):
    if await check_command_blocked(interaction):
        return
    if level < 0 or level > 200:
        await interaction.response.send_message("Volume must be between 0 and 200.", ephemeral=True)
        return

    config = get_guild_config(interaction.guild.id)
    config["volume"] = level
    await save_guild_configs()

    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.source and hasattr(voice_client.source, "volume"):
        voice_client.source.volume = level / 100.0

    await interaction.response.send_message(f"Volume set to {level}%.", ephemeral=True)

@bot.tree.command(name="autoplay", description="Enable or disable autoplay when the queue is empty.")
async def autoplay(interaction: discord.Interaction, enabled: bool):
    if await check_command_blocked(interaction):
        return
    config = get_guild_config(interaction.guild.id)
    config["autoplay"] = enabled
    await save_guild_configs()
    await interaction.response.send_message(
        f"Autoplay is now {'enabled' if enabled else 'disabled'}.",
        ephemeral=True
    )

@bot.tree.command(name="remove", description="Removes a song from the queue by position.")
async def remove(interaction: discord.Interaction, position: int):
    if await check_command_blocked(interaction):
        return

    queue = get_guild_queue(interaction.guild.id)
    if not queue:
        await interaction.response.send_message("The queue is empty.", ephemeral=True)
        return
    index = position - 1
    if index < 0 or index >= len(queue):
        await interaction.response.send_message("Invalid queue position.", ephemeral=True)
        return
    _, title = queue.pop(index)
    await interaction.response.send_message(f"Removed `{title}` from the queue.", ephemeral=True)

@bot.tree.command(name="clear", description="Clears the song queue.")
async def clear(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
        return
    queue = get_guild_queue(interaction.guild.id)
    if queue:
        queue.clear()
        await interaction.response.send_message("Cleared the queue.", ephemeral=True)
    else:
        await interaction.response.send_message("The queue is already empty.", ephemeral=True)

@bot.tree.command(name="skip", description="Skips the currently playing song.")
async def skip(interaction: discord.Interaction):
    if await check_command_blocked(interaction):
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
    if await check_command_blocked(interaction):
        return
    disabled_commands = get_disabled_commands(interaction.guild.id)
    if command_name in disabled_commands:
        await interaction.response.send_message(f"The command `{command_name}` is already disabled.", ephemeral=True)
    elif command_name in [cmd.name for cmd in bot.tree.get_commands()]:
        disabled_commands.add(command_name)
        await interaction.response.send_message(f"The command `{command_name}` has been disabled.", ephemeral=True)
    else:
        await interaction.response.send_message(f"The command `{command_name}` does not exist.", ephemeral=True)


@bot.tree.command(name="enable_command", description="Enables a previously disabled bot command.")
@app_commands.checks.has_permissions(administrator=True)
async def enable_command(interaction: discord.Interaction, command_name: str):
    if await check_command_blocked(interaction):
        return
    disabled_commands = get_disabled_commands(interaction.guild.id)
    if command_name in disabled_commands:
        disabled_commands.discard(command_name)
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
