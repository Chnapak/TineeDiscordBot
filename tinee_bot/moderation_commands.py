import discord
from discord import app_commands

from . import embeds
from . import guards


def setup(bot):
    @bot.tree.command(name="purge", description="Deletes recent messages in this channel.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(interaction: discord.Interaction, amount: int):
        if await guards.check_command_blocked(interaction):
            return
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                embed=embeds.error_embed("Invalid amount", "Amount must be between 1 and 100."),
                ephemeral=True
            )
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=embeds.error_embed("Unavailable", "This command can only be used in text channels."),
                ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await channel.purge(limit=amount)
        await interaction.followup.send(
            embed=embeds.success_embed("Purge complete", f"Deleted {len(deleted)} messages."),
            ephemeral=True
        )

    @bot.tree.command(name="slowmode", description="Sets slowmode for this channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(interaction: discord.Interaction, seconds: int):
        if await guards.check_command_blocked(interaction):
            return
        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message(
                embed=embeds.error_embed("Invalid slowmode", "Slowmode must be 0 to 21600 seconds."),
                ephemeral=True
            )
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=embeds.error_embed("Unavailable", "This command can only be used in text channels."),
                ephemeral=True
            )
            return
        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            message = "Slowmode disabled."
        else:
            message = f"Slowmode set to {seconds}s."
        await interaction.response.send_message(
            embed=embeds.success_embed("Slowmode", message),
            ephemeral=True
        )

    @bot.tree.command(name="lockdown", description="Locks this channel for @everyone.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lockdown(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=embeds.error_embed("Unavailable", "This command can only be used in text channels."),
                ephemeral=True
            )
            return
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(
            embed=embeds.success_embed("Lockdown", "Channel locked for @everyone."),
            ephemeral=True
        )

    @bot.tree.command(name="unlock", description="Unlocks this channel for @everyone.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                embed=embeds.error_embed("Unavailable", "This command can only be used in text channels."),
                ephemeral=True
            )
            return
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(
            embed=embeds.success_embed("Lockdown", "Channel unlocked for @everyone."),
            ephemeral=True
        )

    @purge.error
    @slowmode.error
    @lockdown.error
    @unlock.error
    async def moderation_error(interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                embed=embeds.error_embed("Permission denied", "You don't have permission to use this command."),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=embeds.error_embed("Error", "An error occurred. Please try again."),
                ephemeral=True
            )
