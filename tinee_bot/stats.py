from . import db


ALLOWED_FIELDS = {"ai_responses", "songs_played", "commands_used", "reminders_sent"}


async def increment_stat(guild_id, field, amount=1):
    if not guild_id or field not in ALLOWED_FIELDS:
        return
    query = (
        f"INSERT INTO stats (guild_id, {field}) VALUES (?, ?) "
        f"ON CONFLICT(guild_id) DO UPDATE SET {field} = {field} + ?"
    )
    await db.execute(query, (guild_id, amount, amount))


async def get_stats(guild_id):
    row = await db.fetch_one(
        "SELECT ai_responses, songs_played, commands_used, reminders_sent FROM stats WHERE guild_id = ?",
        (guild_id,)
    )
    if not row:
        return {
            "ai_responses": 0,
            "songs_played": 0,
            "commands_used": 0,
            "reminders_sent": 0
        }
    return {
        "ai_responses": row[0],
        "songs_played": row[1],
        "commands_used": row[2],
        "reminders_sent": row[3]
    }
