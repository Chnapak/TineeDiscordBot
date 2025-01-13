# Importants - everything is important
import os
from dotenv import load_dotenv
import openai
import discord
from discord.ext import commands
from discord import app_commands
                                                                                        #KEYS#
# Getting the tokens and keys from the .env file.
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Control to let the user know if he forgot to set up the .env file.
if not DISCORD_TOKEN or not OPENAI_API_KEY:
    raise ValueError("DISCORD_TOKEN or OPENAI_API_KEY not set up in the .env file")
  
                                                                                    #SETTING BOT UP#
# Setting up the OpenAI API
openai.api_key = OPENAI_API_KEY

# Setting up the Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

                                                                                    #BOT EVENTS#
# Runs when the Discord bot goes online
@bot.event
async def on_ready():
    print(f"Bot is online under the username of {bot.user}")
  
    try:
        synced = await bot.tree.sync()
        print(f"Synchronized {len(synced)} commands.")
    except Exception as e:
        print(f"Error when synchronizing commands: {e}")

# Ping-pong (No longer in use)
#@bot.event
#async def on_message(message):
    #if message.author.bot:
        #return
      
    #if "ping" in message.content.lower():
        #await message.channel.send("pong")

# Reaction on the call of the name Tinee
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower().contains("tinee"):
        # Optional thing to say
        #await message.channel.send("Chvilku, přemýšlím...")
      
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                store=True,
                messages=[
                    {"role": "system", "content": "Your name Tinee, you use she/her pronouns, you always respond in the language of the chatter. Be sure to keep your messages short to feel realistic. Word personality can be described with these adjectives: sarcastic, funny, not bragging, knowledgable, proud, lazy."},
                    {"role": "user", "content": message}
                ]
            )
            await message.channel.send(response.choices[0].message['content'].strip())
        except Exception as e:
            await message.channel.send("Something happend, try again please.")
    else:
        await bot.process_commands(message)

                                                                                    #BOT COMMANDS#
# /greeting
@bot.tree.command(name="greeting", description="Sends one back!")
async def pozdrav(interaction: discord.Interaction):
    print(f"{interaction.user.mention} used /greeting")
    await interaction.response.send_message(f"Hello, {interaction.user.mention}!")


# /question (no longer in use)
#@bot.tree.command(name="question", description="Ask ChatGPT a question.")
#async def dotaz(interaction: discord.Interaction, otazka: str):
    #print(f"{interaction.user.mention} položil otázku: {otazka}")
    #await interaction.response.defer()
  
    #try:
        #response = openai.chat.completions.create(
            #model="gpt-3.5-turbo",
            #store=True,
        #messages=[
            #{"role": "system", "content": "Your name Tinee, you use she/her pronouns, you always respond in the language of the chatter"},
            #{"role": "user", "content": otazka}
        #]
        #)
        #await interaction.followup.send(f"{response.choices[0].message.content}")
    #except Exception as e:
        #await interaction.followup.send(f"Došlo k chybě: {e}")

bot.run(DISCORD_TOKEN)
