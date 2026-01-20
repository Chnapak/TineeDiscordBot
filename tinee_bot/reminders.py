import time
import asyncio

from . import db
from . import state
from . import stats


async def add_reminder(guild_id, channel_id, user_id, message, remind_at):
    await db.execute(
        "INSERT INTO reminders (guild_id, channel_id, user_id, message, remind_at) VALUES (?, ?, ?, ?, ?)",
        (guild_id, channel_id, user_id, message, remind_at)
    )


async def _get_due_reminders(now_ts):
    return await db.fetch_all(
        "SELECT id, guild_id, channel_id, user_id, message FROM reminders WHERE remind_at <= ?",
        (now_ts,)
    )


async def _delete_reminder(reminder_id):
    await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))


async def _get_next_reminder_time():
    row = await db.fetch_one("SELECT MIN(remind_at) FROM reminders", ())
    if not row or row[0] is None:
        return None
    return int(row[0])


async def reminder_loop(bot):
    while True:
        now_ts = int(time.time())
        due = await _get_due_reminders(now_ts)
        for reminder_id, guild_id, channel_id, user_id, message in due:
            try:
                guild = bot.get_guild(guild_id) if guild_id else None
                channel = guild.get_channel(channel_id) if guild else None
                user = guild.get_member(user_id) if guild else None
                if channel:
                    await channel.send(f"{user.mention if user else ''} Reminder: {message}")
                elif user:
                    await user.send(f"Reminder: {message}")
                await stats.increment_stat(guild_id, "reminders_sent", 1)
            finally:
                await _delete_reminder(reminder_id)

        next_time = await _get_next_reminder_time()
        if not next_time:
            await asyncio.sleep(10)
            continue
        delay = max(5, min(60, next_time - int(time.time())))
        await asyncio.sleep(delay)


def start_reminder_loop(bot):
    if state.reminder_loop_started:
        return
    state.reminder_loop_started = True
    bot.loop.create_task(reminder_loop(bot))
