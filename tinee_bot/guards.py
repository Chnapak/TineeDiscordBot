import discord

from . import embeds
from . import storage


async def check_command_blocked(interaction: discord.Interaction, allow_when_sleeping=False, require_guild=True):
    if require_guild and not interaction.guild:
        await interaction.response.send_message(
            embed=embeds.error_embed("Unavailable", "This command can only be used in a server."),
            ephemeral=True
        )
        return True
    if interaction.guild:
        guild_id = interaction.guild.id
        disabled_commands = storage.get_disabled_commands(guild_id)
        if interaction.command and interaction.command.name in disabled_commands:
            await interaction.response.send_message(
                embed=embeds.error_embed(
                    "Command disabled",
                    f"The command `{interaction.command.name}` is currently disabled."
                ),
                ephemeral=True
            )
            return True
        if storage.is_guild_sleeping(guild_id) and not allow_when_sleeping:
            await interaction.response.send_message(
                embed=embeds.error_embed("Asleep", "Tinee is asleep. Use /wake to wake her."),
                ephemeral=True
            )
            return True
    return False
