from datetime import datetime, timezone

import discord


def make_embed(title=None, description=None, color=None):
    if color is None:
        color = discord.Color.blurple()
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text="Tinee")
    return embed


def info_embed(title, description=None):
    return make_embed(title=title, description=description, color=discord.Color.blurple())


def success_embed(title, description=None):
    return make_embed(title=title, description=description, color=discord.Color.green())


def error_embed(title, description=None):
    return make_embed(title=title, description=description, color=discord.Color.red())
