import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

                                                                                        #KEYS#

if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("DISCORD_TOKEN nebo OPENAI_API_KEY není nastavený v souboru .env")


openai.api_key = OPENAI_API_KEY


intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(command_prefix="!", intents=intents)


                                                                                    #SETTING BOT UP#

@bot.event
async def on_ready():
    print(f"Bot je online jako {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synchronizováno {len(synced)} příkazů.")
    except Exception as e:
        print(f"Chyba při synchronizaci příkazů: {e}")

@bot.tree.command(name="pozdrav", description="Pošle pozdrav!")
async def pozdrav(interaction: discord.Interaction):
    print(f"{interaction.user.mention} použil příkaz /pozdrav")
    await interaction.response.send_message(f"Ahoj, {interaction.user.mention}!")


@bot.tree.command(name="dotaz", description="Polož otázku ChatGPT.")
async def dotaz(interaction: discord.Interaction, otazka: str):
    print(f"{interaction.user.mention} položil otázku: {otazka}")
    await interaction.response.defer()
    try:

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            store=True,
        messages=[
            {"role": "system", "content": "Odpovídej vždy co nejstručněji."},
            {"role": "user", "content": otazka}
        ]
        )
        await interaction.followup.send(f"🤔 Odpověď: {response.choices[0].message.content}")
    except Exception as e:
        await interaction.followup.send(f"Došlo k chybě: {e}")


                                                                                    #BOT EVENTS#

@bot.event
async def on_message(message):

    if message.author.bot:
        return
    if "ping" in message.content.lower():
        await message.channel.send("pong")
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower().startswith("bote"):
        prompt = message.content[5:].strip()
        if not prompt:
            await message.channel.send("Jak ti mohu pomoci?")
            return
        
        await message.channel.send("Chvilku, přemýšlím...")
        try:

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

bot.run(DISCORD_TOKEN)
