from asyncio import Lock
from datetime import datetime, timezone

BOT_START_TIME = datetime.now(timezone.utc)

user_chats = {}
guild_configs = {}
user_locks = {}
sleeping_guilds = set()
disabled_commands_by_guild = {}
song_queues = {}
last_song_titles = {}
current_tracks = {}

user_chats_lock = Lock()
guild_configs_lock = Lock()

commands_synced = False
config_api_started = False
config_api_runner = None
