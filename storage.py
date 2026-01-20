import asyncio
import json

import settings
import state


def load_user_chats():
    try:
        with open(settings.USER_CHATS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            if data and all(isinstance(v, list) for v in data.values()):
                state.user_chats = {"_legacy": data}
            else:
                state.user_chats = data
        else:
            state.user_chats = {}
    except (FileNotFoundError, json.JSONDecodeError):
        state.user_chats = {}


def save_user_chats_sync():
    with open(settings.USER_CHATS_FILE, "w", encoding="utf-8") as file:
        json.dump(state.user_chats, file)


async def save_user_chats():
    async with state.user_chats_lock:
        await asyncio.to_thread(save_user_chats_sync)


def load_guild_configs():
    try:
        with open(settings.CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            state.guild_configs = data
        else:
            state.guild_configs = {}
    except (FileNotFoundError, json.JSONDecodeError):
        state.guild_configs = {}


def save_guild_configs_sync():
    with open(settings.CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(state.guild_configs, file)


async def save_guild_configs():
    async with state.guild_configs_lock:
        await asyncio.to_thread(save_guild_configs_sync)


def new_guild_config():
    return {
        "ai_enabled": True,
        "ai_trigger": "keyword",
        "ai_keyword": "tinee",
        "ai_channels": [],
        "autoplay": False,
        "volume": 100
    }


def normalize_guild_config(config):
    if not isinstance(config, dict):
        return new_guild_config()
    if "ai_enabled" not in config:
        config["ai_enabled"] = True
    if "ai_trigger" not in config:
        config["ai_trigger"] = "keyword"
    if "ai_keyword" not in config:
        config["ai_keyword"] = "tinee"
    if "ai_channels" not in config:
        config["ai_channels"] = []
    if "autoplay" not in config:
        config["autoplay"] = False
    if "volume" not in config:
        config["volume"] = 100

    config["ai_enabled"] = bool(config.get("ai_enabled"))
    trigger = str(config.get("ai_trigger", "keyword")).lower()
    if trigger not in ("keyword", "mention", "both"):
        trigger = "keyword"
    config["ai_trigger"] = trigger

    keyword = str(config.get("ai_keyword", "tinee")).strip()
    config["ai_keyword"] = keyword if keyword else "tinee"

    channels = config.get("ai_channels", [])
    if not isinstance(channels, list):
        channels = []
    normalized_channels = []
    for channel_id in channels:
        try:
            normalized_channels.append(int(channel_id))
        except (TypeError, ValueError):
            continue
    config["ai_channels"] = normalized_channels

    config["autoplay"] = bool(config.get("autoplay"))
    try:
        volume = int(config.get("volume", 100))
    except (TypeError, ValueError):
        volume = 100
    config["volume"] = max(0, min(200, volume))
    return config


def get_guild_config(guild_id):
    guild_key = str(guild_id)
    if guild_key not in state.guild_configs:
        state.guild_configs[guild_key] = new_guild_config()
    state.guild_configs[guild_key] = normalize_guild_config(state.guild_configs[guild_key])
    return state.guild_configs[guild_key]


def get_or_create_user_history(guild_id, user_id):
    guild_key = str(guild_id)
    user_key = str(user_id)
    if guild_key not in state.user_chats:
        state.user_chats[guild_key] = {}
    guild_chats = state.user_chats[guild_key]
    if user_key not in guild_chats:
        legacy = state.user_chats.get("_legacy", {})
        if user_key in legacy:
            guild_chats[user_key] = legacy.pop(user_key)
            if not legacy:
                state.user_chats.pop("_legacy", None)
        else:
            guild_chats[user_key] = [{"role": "system", "content": settings.SYSTEM_PROMPT}]
    return guild_chats[user_key]


def is_guild_sleeping(guild_id):
    return guild_id in state.sleeping_guilds


def get_disabled_commands(guild_id):
    if guild_id not in state.disabled_commands_by_guild:
        state.disabled_commands_by_guild[guild_id] = set()
    return state.disabled_commands_by_guild[guild_id]


async def get_user_lock(guild_id, user_id):
    lock_key = f"{guild_id}:{user_id}"
    if lock_key not in state.user_locks:
        state.user_locks[lock_key] = asyncio.Lock()
    return state.user_locks[lock_key]
