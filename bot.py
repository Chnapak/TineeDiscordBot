import discord
from discord.ext import commands

from tinee_bot import admin_commands
from tinee_bot import ai
from tinee_bot import db
from tinee_bot import moderation_commands
from tinee_bot import music
from tinee_bot import reminders
from tinee_bot import settings
from tinee_bot import state
from tinee_bot import stats
from tinee_bot import storage
from tinee_bot import user_commands
from tinee_bot import web_api


if not settings.DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not set up in the .env file")


intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.tree.interaction_check
async def track_usage(interaction: discord.Interaction):
    if interaction.guild_id:
        await stats.increment_stat(interaction.guild_id, "commands_used", 1)
    return True


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name="/help")
    )
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
    reminders.start_reminder_loop(bot)
    if settings.CONFIG_API_ENABLED and not state.config_api_started:
        state.config_api_started = True
        bot.loop.create_task(web_api.start_config_api(bot))


@bot.event
async def on_message(message):
    await ai.handle_message(bot, message)


storage.load_user_chats()
storage.load_guild_configs()
db.init_db()

user_commands.setup(bot)
music.setup(bot)
admin_commands.setup(bot)
moderation_commands.setup(bot)


bot.run(settings.DISCORD_TOKEN)
