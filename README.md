# TineeDiscordBot

A Discord bot with slash commands, AI chat replies, and basic music playback.

## Features
- AI replies with short, in-character responses and per-server configuration.
- Music playback via YouTube search with per-guild queues.
- Admin controls: `/sleep`, `/wake`, `/disable_command`, `/enable_command`.
- Persistent user chat history in `user_chats.json`.

## Requirements
- Python 3.10+
- ffmpeg (available on PATH or configured with `FFMPEG_PATH`)
- Discord bot token

## Setup
1. Create a Discord application and bot, then enable the Message Content intent.
2. Copy `.env.example` to `.env` and fill in your values.
3. Install dependencies:

```bash
pip install -U discord.py[voice] openai python-dotenv yt-dlp
```

4. Run the bot:

```bash
python bot.py
```

## Environment variables
- `DISCORD_TOKEN` (required): your bot token.
- `OPENAI_API_KEY` (optional): enables AI replies.
- `OPENAI_MODEL` (optional): defaults to `gpt-4`.
- `FFMPEG_PATH` (optional): path to `ffmpeg` binary if not on PATH.

## Commands
- `/greeting`: say hi.
- `/sleep` / `/wake`: pause or resume command handling (admin only).
- `/join` / `/leave`: connect or disconnect from voice.
- `/play <query>`: search and play a track.
- `/pause` / `/resume`: control playback.
- `/queue`: show the current queue.
- `/skip`: skip the current track.
- `/disable_command <name>` / `/enable_command <name>`: toggle a command (admin only).
- `/config`: show current per-server AI settings (admin only).
- `/set_ai <enabled>`: enable/disable AI replies (admin only).
- `/set_ai_trigger <keyword|mention|both> [keyword]`: set trigger mode, optionally update keyword (admin only).
- `/set_ai_keyword <keyword>`: update the keyword trigger (admin only).
- `/allow_ai_channel <channel>`: allow AI replies in a channel (admin only).
- `/block_ai_channel <channel>`: block AI replies in a channel (admin only).
- `/clear_ai_channels`: allow AI replies in all channels (admin only).

## Notes
- The bot only responds in servers (not DMs).
- AI replies can trigger by keyword, mention, or both depending on per-server config.
