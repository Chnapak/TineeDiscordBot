import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands

# Načtení proměnných prostředí
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Kontrola, zda jsou klíče nastavené
if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("DISCORD_TOKEN nebo OPENAI_API_KEY není nastavený v souboru .env")

# Nastavení OpenAI API klíče
openai.api_key = OPENAI_API_KEY

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
    print(f"{interaction.user.mention} použil příkaz /pozdrav")
    await interaction.response.send_message(f"Ahoj, {interaction.user.mention}!")

# Slash command pro OpenAI generování odpovědi
@bot.tree.command(name="dotaz", description="Polož otázku ChatGPT.")
async def dotaz(interaction: discord.Interaction, otazka: str):
    print(f"{interaction.user.mention} položil otázku: {otazka}")
    await interaction.response.defer()  # Odloží odpověď (pro delší dobu zpracování)
    try:
                # Volání OpenAI API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # Model ChatGPT
            store=True,
        messages=[
            {"role": "system", "content": "Odpovídej vždy co nejstručněji."},
            {"role": "user", "content": otazka}
        ]
        )
        await interaction.followup.send(f"🤔 Odpověď: {response.choices[0].message.content}")
    except Exception as e:
        await interaction.followup.send(f"Došlo k chybě: {e}")

# Událost při přijetí zprávy
@bot.event
async def on_message(message):
    # Kontrola, jestli zpráva pochází od uživatele a obsahuje "ping"
    if message.author.bot:
        return  # Ignoruje zprávy od botů
    if "ping" in message.content.lower():  # Porovnání malými písmeny
        await message.channel.send("pong")  # Odpověď do stejného kanálu
@bot.event
async def on_message(message):
    # Ignoruje zprávy od botů
    if message.author.bot:
        return

    # Zpracování zpráv začínajících "bote"
    if message.content.lower().startswith("bote"):
        prompt = message.content[5:].strip()  # Odstraní "bote" z textu
        if not prompt:
            await message.channel.send("Jak ti mohu pomoci?")
            return
        
        await message.channel.send("Chvilku, přemýšlím...")
        try:
            # Volání OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Odpovídej stručně, jasně a v jazyce otázky."},
                    {"role": "user", "content": prompt}
                ]
            )
            await message.channel.send(response.choices[0].message['content'].strip())
        except Exception as e:
            await message.channel.send("Něco se pokazilo. Zkus to prosím znovu.")
    else:
        await bot.process_commands(message)

# Spuštění bota
bot.run(DISCORD_TOKEN)
