import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

CONFIG_API_ENABLED = os.getenv("CONFIG_API_ENABLED", "false").lower() == "true"
CONFIG_API_HOST = os.getenv("CONFIG_API_HOST", "127.0.0.1")
CONFIG_API_PORT = os.getenv("CONFIG_API_PORT", "8080")
CONFIG_API_TOKEN = os.getenv("CONFIG_API_TOKEN")
DB_FILE = os.getenv("DB_FILE", "bot_data.db")
AI_COOLDOWN_SECONDS = os.getenv("AI_COOLDOWN_SECONDS", "10")
AI_GUILD_RATE_LIMIT = os.getenv("AI_GUILD_RATE_LIMIT", "30")
AI_GUILD_WINDOW_SECONDS = os.getenv("AI_GUILD_WINDOW_SECONDS", "60")

try:
    CONFIG_API_PORT = int(CONFIG_API_PORT)
except ValueError:
    CONFIG_API_PORT = 8080

try:
    AI_COOLDOWN_SECONDS = int(AI_COOLDOWN_SECONDS)
except ValueError:
    AI_COOLDOWN_SECONDS = 10

try:
    AI_GUILD_RATE_LIMIT = int(AI_GUILD_RATE_LIMIT)
except ValueError:
    AI_GUILD_RATE_LIMIT = 30

try:
    AI_GUILD_WINDOW_SECONDS = int(AI_GUILD_WINDOW_SECONDS)
except ValueError:
    AI_GUILD_WINDOW_SECONDS = 60


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
USER_CHATS_FILE = "user_chats.json"

MAX_REMINDER_SECONDS = 7 * 24 * 60 * 60
POLL_EMOJIS = ["1\u20e3", "2\u20e3", "3\u20e3", "4\u20e3", "5\u20e3", "6\u20e3", "7\u20e3", "8\u20e3", "9\u20e3", "\U0001F51F"]
QUOTES = [
    "Keep it simple, keep it fun.",
    "Small steps beat no steps.",
    "Progress, not perfection.",
    "If it works, it ships.",
    "Less noise, more signal.",
    "Make it work, then make it nice.",
    "Stay curious.",
    "Bugs fear the patient.",
    "Build, learn, repeat.",
    "One thing at a time."
]
