import os
from dotenv import load_dotenv

# Načtení proměnných prostředí
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

import discord
from discord.ext import commands
from discord import app_commands

# Nastavení intents (potřebné pro správnou funkci)
intents = discord.Intents.default()
intents.message_content = True

# Vytvoření instance bota
bot = commands.Bot(command_prefix="!", intents=intents)

# Událost při spuštění bota
@bot.event
async def on_ready():
    print(f"Bot je online jako {bot.user}")
    try:
        synced = await bot.tree.sync()  # Synchronizuje slash commandy
        print(f"Synchronizováno {len(synced)} příkazů.")
    except Exception as e:
        print(f"Chyba při synchronizaci příkazů: {e}")

# Příklad jednoduchého slash commandu
@bot.tree.command(name="pozdrav", description="Pošle pozdrav!")
async def pozdrav(interaction: discord.Interaction):
    print(f"{interaction.user.mention} pouzil prikaz /pozdrav")
    await interaction.response.send_message(f"Ahoj, {interaction.user.mention}!")

# Událost při přijetí zprávy
@bot.event
async def on_message(message):
    # Kontrola, jestli zpráva pochází od uživatele a obsahuje "ping"
    if message.author.bot:
        return  # Ignoruje zprávy od botů
    if "ping" in message.content.lower():  # Porovnání malými písmeny
        await message.channel.send("pong")  # Odpověď do stejného kanálu

    await bot.process_commands(message)  # Umožní zpracovat příkazy


# Spuštění bota
bot.run(DISCORD_TOKEN)
