import discord
from discord.ext import commands

from tinee_bot import admin_commands
from tinee_bot import ai
from tinee_bot import music
from tinee_bot import settings
from tinee_bot import state
from tinee_bot import storage
from tinee_bot import user_commands
from tinee_bot import web_api


if not settings.DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not set up in the .env file")


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not state.commands_synced:
        state.commands_synced = True
        try:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global commands")
        except Exception as e:
            print(f"Failed to sync global commands: {e}")
        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                print(f"Synced {len(synced)} commands to guild {guild.id}")
            except Exception as e:
                print(f"Failed to sync commands for guild {guild.id}: {e}")
    if settings.CONFIG_API_ENABLED and not state.config_api_started:
        state.config_api_started = True
        bot.loop.create_task(web_api.start_config_api(bot))


@bot.event
async def on_message(message):
    await ai.handle_message(bot, message)


storage.load_user_chats()
storage.load_guild_configs()

user_commands.setup(bot)
music.setup(bot)
admin_commands.setup(bot)


bot.run(settings.DISCORD_TOKEN)
