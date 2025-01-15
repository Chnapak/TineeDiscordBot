import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands
from discord import FFmpegPCMAudio
import yt_dlp as youtube_dl

# KEYS
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("DISCORD_TOKEN or OPENAI_API_KEY not set up in the .env file")

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


@bot.event
async def on_message(message):
    global is_sleeping

    if is_sleeping or message.author.bot or not message.guild:
        return

    if "tinee" in message.content.lower():
        user_id = str(message.author.id)
        if user_id not in user_chats:
            user_chats[user_id] = [
                {"role": "system", "content": "Your name is Tinee, you use she/her pronouns. Keep your messages short to feel realistic."}
            ]

        user_chats[user_id].append({"role": "user", "content": message.content})

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=user_chats[user_id]
            )
            bot_response = response.choices[0].message.content
            user_chats[user_id].append({"role": "assistant", "content": bot_response})
            await message.channel.send(bot_response)
        except Exception as e:
            print(f"OpenAI error: {e}")
            await message.channel.send("Something went wrong, try again later.")
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


@bot.tree.command(name="play", description="Plays a song in the voice channel.")
async def play(interaction: discord.Interaction, search: str):
    if await check_command_disabled(interaction):
        return
    voice_client = interaction.guild.voice_client

    if not voice_client:
        await interaction.response.send_message("I'm not connected to a voice channel! Use `/join` to invite me.", ephemeral=True)
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
    }

    await interaction.response.defer()

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)
            url = info['entries'][0]['url']
        except Exception as e:
            await interaction.followup.send("Couldn't find the song. Try a different search.", ephemeral=True)
            return

    audio_source = FFmpegPCMAudio(url, executable="C:/Users/atlan/Desktop/bot/ffmpeg/bin/ffmpeg.exe")
    if not voice_client.is_playing():
        voice_client.play(audio_source, after=lambda e: print(f"Finished playing: {e}"))
        await interaction.followup.send(f"Now playing: {search}")
    else:
        await interaction.followup.send("I'm already playing a song. Please wait for the current track to finish.", ephemeral=True)


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
