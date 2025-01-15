import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands

# KEYS
# Getting the tokens and keys from the .env file.
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Control to let the user know if he forgot to set up the .env file.
if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("DISCORD_TOKEN or OPENAI_API_KEY not set up in the .env file")

# SETTING BOT UP
# Setting up the OpenAI API
openai.api_key = OPENAI_API_KEY

# Setting up the Discord bot
intents = discord.Intents.default()
intents.messages = True  # Ensure this intent is enabled
intents.message_content = True  # Required for accessing message content
bot = commands.Bot(command_prefix="!", intents=intents)

# BOT EVENTS
# Global variable to track if the bot is sleeping
is_sleeping = False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()  # Sync application commands
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    global is_sleeping

    if is_sleeping:
        return  # Ignore all messages if bot is sleeping

    if message.author.bot or not message.guild:  # Ignore bots and DMs
        return

    if "tinee" in message.content.lower():
        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Your name is Tinee, you use she/her pronouns. Keep your messages short to feel realistic."},
                    {"role": "user", "content": message.content}
                ]
            )
            await message.channel.send(response.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI error: {e}")
            await message.channel.send("Something went wrong, try again later.")
    else:
        await bot.process_commands(message)

# BOT COMMANDS
# /greeting
@bot.tree.command(name="greeting", description="Sends one back!")
async def pozdrav(interaction: discord.Interaction):
    global is_sleeping

    if is_sleeping:
        await interaction.response.send_message("Tinee is sleeping. She can't respond right now.", ephemeral=True)
        return

    print(f"{interaction.user.display_name} used /greeting")
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

# /sleep
@bot.tree.command(name="sleep", description="Tells Tinee to go to sleep.")
@app_commands.checks.has_permissions(administrator=True)
async def sleep(interaction: discord.Interaction):
    global is_sleeping
    is_sleeping = True
    await interaction.response.send_message("Tinee is now asleep. She won't respond to commands.", ephemeral=True)

# /wake
@bot.tree.command(name="wake", description="Wakes Tinee up.")
@app_commands.checks.has_permissions(administrator=True)
async def wake(interaction: discord.Interacimport os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands

# KEYS
# Getting the tokens and keys from the .env file.
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Control to let the user know if he forgot to set up the .env file.
if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("DISCORD_TOKEN or OPENAI_API_KEY not set up in the .env file")

# SETTING BOT UP
# Setting up the OpenAI API
openai.api_key = OPENAI_API_KEY

# Setting up the Discord bot
intents = discord.Intents.default()
intents.messages = True  # Ensure this intent is enabled
intents.message_content = True  # Required for accessing message content
bot = commands.Bot(command_prefix="!", intents=intents)

# BOT EVENTS
# Global variable to track if the bot is sleeping
is_sleeping = False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()  # Sync application commands
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Přidáme globální slovník pro sledování historie chatů uživatelů
user_chats = {}

@bot.event
async def on_message(message):
    global is_sleeping

    if is_sleeping or message.author.bot or not message.guild:  # Ignoruj bota a DM
        return

    if "tinee" in message.content.lower():
        user_id = str(message.author.id)  # Unikátní identifikátor uživatele
        if user_id not in user_chats:
            # Pokud uživatel nemá historii, vytvoříme nový chat kontext
            user_chats[user_id] = [
                {"role": "system", "content": "Your name is Tinee, you use she/her pronouns. Keep your messages short to feel realistic."}
            ]
        
        # Přidáme aktuální zprávu uživatele do historie
        user_chats[user_id].append({"role": "user", "content": message.content})
        
        try:
            # Posíláme celou historii chatu uživatele do OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=user_chats[user_id]
            )
            
            # Získáme odpověď a přidáme ji do historie
            bot_response = response.choices[0].message.content
            user_chats[user_id].append({"role": "assistant", "content": bot_response})
            
            # Odpovíme v kanálu
            await message.channel.send(bot_response)
        except Exception as e:
            print(f"OpenAI error: {e}")
            await message.channel.send("Something went wrong, try again later.")
    else:
        await bot.process_commands(message)


# BOT COMMANDS
# /greeting
@bot.tree.command(name="greeting", description="Sends one back!")
async def pozdrav(interaction: discord.Interaction):
    global is_sleeping

    if is_sleeping:
        await interaction.response.send_message("Tinee is sleeping. She can't respond right now.", ephemeral=True)
        return

    print(f"{interaction.user.display_name} used /greeting")
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

# /sleep
@bot.tree.command(name="sleep", description="Tells Tinee to go to sleep.")
@app_commands.checks.has_permissions(administrator=True)
async def sleep(interaction: discord.Interaction):
    global is_sleeping
    is_sleeping = True
    await interaction.response.send_message("Tinee is now asleep. She won't respond to commands.", ephemeral=True)

# /wake
@bot.tree.command(name="wake", description="Wakes Tinee up.")
@app_commands.checks.has_permissions(administrator=True)
async def wake(interaction: discord.Interaction):
    global is_sleeping
    is_sleeping = False
    await interaction.response.send_message("Tinee is awake and ready to help!", ephemeral=True)

# Přidáme slash command na vymazání historie chatu
@bot.tree.command(name="clear_chat", description="Clears your chat history with Tinee.")
async def clear_chat(interaction: discord.Interaction):
    user_id = str(interaction.user.id)  # Unikátní ID uživatele
    
    if user_id in user_chats:
        del user_chats[user_id]  # Vymaže historii chatu uživatele
        await interaction.response.send_message("Your chat history has been cleared.", ephemeral=True)
    else:
        await interaction.response.send_message("You don't have any chat history to clear.", ephemeral=True)


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
tion):
    global is_sleeping
    is_sleeping = False
    await interaction.response.send_message("Tinee is awake and ready to help!", ephemeral=True)

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
