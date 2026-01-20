import asyncio
import time

import openai

from . import settings
from . import state
from . import stats
from . import storage


openai.api_key = settings.OPENAI_API_KEY


def should_respond_to_message(message, bot, config):
    if not config.get("ai_enabled", True):
        return False
    allowed_channels = config.get("ai_channels", [])
    if allowed_channels and message.channel.id not in allowed_channels:
        return False

    trigger = config.get("ai_trigger", "keyword")
    keyword = str(config.get("ai_keyword", "tinee")).lower()
    content = (message.content or "").lower()
    is_mentioned = bot.user in message.mentions if bot.user else False

    if trigger == "mention":
        return is_mentioned
    if trigger == "both":
        return (keyword and keyword in content) or is_mentioned
    return keyword and keyword in content


async def fetch_openai_response(messages):
    def _call_openai():
        return openai.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages
        )
    return await asyncio.to_thread(_call_openai)


def _is_user_rate_limited(user_id, now_ts):
    cooldown = settings.AI_COOLDOWN_SECONDS
    if cooldown <= 0:
        return False
    last_ts = state.ai_user_last_response.get(user_id)
    if not last_ts:
        return False
    return (now_ts - last_ts) < cooldown


def _is_guild_rate_limited(guild_id, now_ts):
    limit = settings.AI_GUILD_RATE_LIMIT
    window = settings.AI_GUILD_WINDOW_SECONDS
    if limit <= 0 or window <= 0:
        return False
    recent = state.ai_guild_recent_responses.get(guild_id, [])
    recent = [ts for ts in recent if (now_ts - ts) <= window]
    state.ai_guild_recent_responses[guild_id] = recent
    return len(recent) >= limit


async def handle_message(bot, message):
    if message.author.bot or not message.guild:
        return
    guild_id = message.guild.id
    if storage.is_guild_sleeping(guild_id):
        return

    config = storage.get_guild_config(guild_id)
    if not should_respond_to_message(message, bot, config):
        await bot.process_commands(message)
        return

    user_id = message.author.id
    now_ts = int(time.time())
    if _is_user_rate_limited(user_id, now_ts) or _is_guild_rate_limited(guild_id, now_ts):
        await bot.process_commands(message)
        return

    user_lock = await storage.get_user_lock(guild_id, user_id)
    async with user_lock:
        history = storage.get_or_create_user_history(guild_id, user_id)

        history.append({"role": "user", "content": message.content})

        max_messages = 100
        if len(history) > max_messages:
            system_prompt = history[0] if history and history[0].get("role") == "system" else None
            recent = history[-(max_messages - 1):]
            if system_prompt and system_prompt not in recent:
                new_history = [system_prompt] + recent
            else:
                new_history = recent
            history.clear()
            history.extend(new_history)

        if not settings.OPENAI_API_KEY:
            await message.channel.send(
                "Nem\u00e1m p\u0159\u00edstup k OpenAI API, tak\u017ee nem\u016f\u017eu odpov\u011bd\u011bt. "
                "Zkuste to pros\u00edm pozd\u011bji!"
            )
            return

        try:
            response = await fetch_openai_response(history)
            bot_response = response.choices[0].message.content
            history.append({"role": "assistant", "content": bot_response})
            await message.channel.send(bot_response)
            response_ts = int(time.time())
            state.ai_user_last_response[user_id] = response_ts
            recent = state.ai_guild_recent_responses.get(guild_id, [])
            window = settings.AI_GUILD_WINDOW_SECONDS
            if window > 0:
                recent = [ts for ts in recent if (response_ts - ts) <= window]
            else:
                recent = []
            recent.append(response_ts)
            state.ai_guild_recent_responses[guild_id] = recent
            await stats.increment_stat(guild_id, "ai_responses", 1)
        except Exception as e:
            print(f"OpenAI error: {e}")
            await message.channel.send("Something went wrong, try again later.")

        await storage.save_user_chats()
