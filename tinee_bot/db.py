import asyncio
import sqlite3

from . import settings


def init_db():
    conn = sqlite3.connect(settings.DB_FILE)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                message TEXT,
                remind_at INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                guild_id INTEGER PRIMARY KEY,
                ai_responses INTEGER DEFAULT 0,
                songs_played INTEGER DEFAULT 0,
                commands_used INTEGER DEFAULT 0,
                reminders_sent INTEGER DEFAULT 0
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reminders_time ON reminders (remind_at)")
        conn.commit()
    finally:
        conn.close()


def _execute(query, params=()):
    conn = sqlite3.connect(settings.DB_FILE)
    try:
        conn.execute(query, params)
        conn.commit()
    finally:
        conn.close()


def _fetch_one(query, params=()):
    conn = sqlite3.connect(settings.DB_FILE)
    try:
        cursor = conn.execute(query, params)
        return cursor.fetchone()
    finally:
        conn.close()


def _fetch_all(query, params=()):
    conn = sqlite3.connect(settings.DB_FILE)
    try:
        cursor = conn.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()


async def execute(query, params=()):
    await asyncio.to_thread(_execute, query, params)


async def fetch_one(query, params=()):
    return await asyncio.to_thread(_fetch_one, query, params)


async def fetch_all(query, params=()):
    return await asyncio.to_thread(_fetch_all, query, params)
