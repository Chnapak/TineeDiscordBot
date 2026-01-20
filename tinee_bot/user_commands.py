import asyncio
import random
from datetime import datetime, timezone

import discord

from . import guards
from . import settings
from . import state
from . import utils


def setup(bot):
    @bot.tree.command(name="help", description="Shows available commands.")
    async def help_command(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        embed = discord.Embed(title="Tinee Commands", color=discord.Color.blurple())
        embed.add_field(
            name="User",
            value=(
                "/greeting, /ping, /uptime, /avatar, /userinfo, /serverinfo, "
                "/roll, /coinflip, /choose, /8ball, /poll, /remind, /quote"
            ),
            inline=False
        )
        embed.add_field(
            name="Music",
            value=(
                "/join, /leave, /play, /pause, /resume, /queue, /nowplaying, "
                "/skip, /remove, /clear, /volume, /autoplay"
            ),
            inline=False
        )
        embed.add_field(
            name="Admin",
            value=(
                "/sleep, /wake, /disable_command, /enable_command, /config, "
                "/set_ai, /set_ai_trigger, /set_ai_keyword, /allow_ai_channel, "
                "/block_ai_channel, /clear_ai_channels"
            ),
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="greeting", description="Sends one back!")
    async def greeting(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        await interaction.response.send_message(f"Hello, {interaction.user.mention}!")

    @bot.tree.command(name="ping", description="Shows bot latency.")
    async def ping(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        latency_ms = round(bot.latency * 1000)
        await interaction.response.send_message(f"Pong! {latency_ms}ms")

    @bot.tree.command(name="uptime", description="Shows how long the bot has been running.")
    async def uptime(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        uptime_delta = datetime.now(timezone.utc) - state.BOT_START_TIME
        await interaction.response.send_message(f"Uptime: {utils.format_timedelta(uptime_delta)}")

    @bot.tree.command(name="avatar", description="Shows a user's avatar.")
    async def avatar(interaction: discord.Interaction, member: discord.Member = None):
        if await guards.check_command_blocked(interaction):
            return
        target = member or interaction.user
        embed = discord.Embed(
            title=f"{target.display_name}'s avatar",
            color=discord.Color.blurple()
        )
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="userinfo", description="Shows info about a user.")
    async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
        if await guards.check_command_blocked(interaction):
            return
        target = member or interaction.user
        created_at = target.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        joined_at = "unknown"
        if target.joined_at:
            joined_at = target.joined_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        embed = discord.Embed(title="User info", color=discord.Color.blurple())
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="User", value=f"{target} ({target.id})", inline=False)
        embed.add_field(name="Created", value=created_at, inline=True)
        embed.add_field(name="Joined", value=joined_at, inline=True)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="serverinfo", description="Shows info about the server.")
    async def serverinfo(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        guild = interaction.guild
        created_at = guild.created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        owner = guild.owner.mention if guild.owner else f"<@{guild.owner_id}>"
        embed = discord.Embed(title=guild.name, color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Server ID", value=str(guild.id), inline=False)
        embed.add_field(name="Owner", value=owner, inline=True)
        embed.add_field(name="Members", value=str(guild.member_count), inline=True)
        embed.add_field(name="Text channels", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Voice channels", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Created", value=created_at, inline=True)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="roll", description="Rolls dice.")
    async def roll(interaction: discord.Interaction, sides: int = 6, count: int = 1):
        if await guards.check_command_blocked(interaction):
            return
        if sides < 2 or sides > 1000:
            await interaction.response.send_message("Sides must be between 2 and 1000.", ephemeral=True)
            return
        if count < 1 or count > 20:
            await interaction.response.send_message("Count must be between 1 and 20.", ephemeral=True)
            return
        rolls = [random.randint(1, sides) for _ in range(count)]
        if count == 1:
            message = f"Rolled a D{sides}: {rolls[0]}"
        else:
            total = sum(rolls)
            rolls_text = ", ".join(str(value) for value in rolls)
            message = f"Rolled {count}x D{sides}: {rolls_text} (total {total})"
        await interaction.response.send_message(message)

    @bot.tree.command(name="coinflip", description="Flips a coin.")
    async def coinflip(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        result = random.choice(["Heads", "Tails"])
        await interaction.response.send_message(f"{interaction.user.mention} flipped: {result}")

    @bot.tree.command(name="choose", description="Picks one option from a list.")
    async def choose(interaction: discord.Interaction, options: str):
        if await guards.check_command_blocked(interaction):
            return
        raw = options.replace("|", ",")
        items = [item.strip() for item in raw.split(",") if item.strip()]
        if len(items) < 2:
            await interaction.response.send_message("Provide at least two options.", ephemeral=True)
            return
        if len(items) > 20:
            await interaction.response.send_message("Too many options (max 20).", ephemeral=True)
            return
        choice = random.choice(items)
        await interaction.response.send_message(f"I choose: {choice}")

    @bot.tree.command(name="8ball", description="Ask the magic 8-ball.")
    async def eight_ball(interaction: discord.Interaction, question: str):
        if await guards.check_command_blocked(interaction):
            return
        responses = [
            "It is certain.",
            "It is decidedly so.",
            "Without a doubt.",
            "Yes definitely.",
            "You may rely on it.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful."
        ]
        answer = random.choice(responses)
        await interaction.response.send_message(f"Question: {question}\nAnswer: {answer}")

    @bot.tree.command(name="poll", description="Creates a poll with up to 10 options.")
    async def poll(interaction: discord.Interaction, question: str, options: str):
        if await guards.check_command_blocked(interaction):
            return
        raw = options.replace("|", ",")
        items = [item.strip() for item in raw.split(",") if item.strip()]
        if len(items) < 2:
            await interaction.response.send_message("Provide at least two options.", ephemeral=True)
            return
        if len(items) > 10:
            await interaction.response.send_message("Too many options (max 10).", ephemeral=True)
            return
        embed = discord.Embed(title="Poll", description=question, color=discord.Color.blurple())
        for idx, option in enumerate(items):
            embed.add_field(name=f"{settings.POLL_EMOJIS[idx]} {option}", value="\u200b", inline=False)
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        for idx in range(len(items)):
            await message.add_reaction(settings.POLL_EMOJIS[idx])

    @bot.tree.command(name="remind", description="Sets a reminder (e.g. 10m, 2h, 1h30m).")
    async def remind(interaction: discord.Interaction, in_time: str, message: str):
        if await guards.check_command_blocked(interaction):
            return
        seconds = utils.parse_duration(in_time)
        if not seconds or seconds <= 0:
            await interaction.response.send_message(
                "Invalid time format. Examples: `10m`, `45s`, `2h`, `1h30m`.",
                ephemeral=True
            )
            return
        if seconds > settings.MAX_REMINDER_SECONDS:
            await interaction.response.send_message("Max reminder time is 7 days.", ephemeral=True)
            return
        delay_text = utils.format_seconds(seconds)
        await interaction.response.send_message(f"Okay! I'll remind you in {delay_text}.", ephemeral=True)

        channel_id = interaction.channel_id
        guild_id = interaction.guild_id
        user_id = interaction.user.id
        reminder_text = message

        async def send_reminder():
            await asyncio.sleep(seconds)
            guild = bot.get_guild(guild_id) if guild_id else None
            channel = guild.get_channel(channel_id) if guild else None
            user = guild.get_member(user_id) if guild else None
            if channel:
                await channel.send(f"{user.mention if user else ''} Reminder: {reminder_text}")
            elif user:
                await user.send(f"Reminder: {reminder_text}")

        bot.loop.create_task(send_reminder())

    @bot.tree.command(name="quote", description="Shows a random quote.")
    async def quote(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        await interaction.response.send_message(random.choice(settings.QUOTES))
