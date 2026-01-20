import discord
from discord import app_commands

import guards
import state
import storage


def setup(bot):
    @bot.tree.command(name="sleep", description="Tells Tinee to go to sleep.")
    @app_commands.checks.has_permissions(administrator=True)
    async def sleep(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        state.sleeping_guilds.add(interaction.guild.id)
        await interaction.response.send_message("Tinee is now asleep. She won't respond to commands.", ephemeral=True)

    @bot.tree.command(name="wake", description="Wakes Tinee up.")
    @app_commands.checks.has_permissions(administrator=True)
    async def wake(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction, allow_when_sleeping=True):
            return
        state.sleeping_guilds.discard(interaction.guild.id)
        await interaction.response.send_message("Tinee is awake and ready to help!", ephemeral=True)

    @bot.tree.command(name="disable_command", description="Disables a specific bot command.")
    @app_commands.checks.has_permissions(administrator=True)
    async def disable_command(interaction: discord.Interaction, command_name: str):
        if await guards.check_command_blocked(interaction):
            return
        disabled_commands = storage.get_disabled_commands(interaction.guild.id)
        if command_name in disabled_commands:
            await interaction.response.send_message(
                f"The command `{command_name}` is already disabled.",
                ephemeral=True
            )
        elif command_name in [cmd.name for cmd in bot.tree.get_commands()]:
            disabled_commands.add(command_name)
            await interaction.response.send_message(
                f"The command `{command_name}` has been disabled.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"The command `{command_name}` does not exist.",
                ephemeral=True
            )

    @bot.tree.command(name="enable_command", description="Enables a previously disabled bot command.")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_command(interaction: discord.Interaction, command_name: str):
        if await guards.check_command_blocked(interaction):
            return
        disabled_commands = storage.get_disabled_commands(interaction.guild.id)
        if command_name in disabled_commands:
            disabled_commands.discard(command_name)
            await interaction.response.send_message(
                f"The command `{command_name}` has been enabled.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"The command `{command_name}` is not disabled or does not exist.",
                ephemeral=True
            )

    @bot.tree.command(name="config", description="Shows the current per-server configuration.")
    @app_commands.checks.has_permissions(administrator=True)
    async def config(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        channel_ids = config.get("ai_channels", [])
        if channel_ids:
            channel_labels = []
            for channel_id in channel_ids:
                channel = interaction.guild.get_channel(channel_id)
                channel_labels.append(channel.mention if channel else str(channel_id))
            channels_text = ", ".join(channel_labels)
        else:
            channels_text = "all channels"
        await interaction.response.send_message(
            "AI enabled: {enabled}\nAI trigger: {trigger}\nAI keyword: {keyword}\nAI channels: {channels}\n"
            "Autoplay: {autoplay}\nVolume: {volume}%".format(
                enabled=config.get("ai_enabled", True),
                trigger=config.get("ai_trigger", "keyword"),
                keyword=config.get("ai_keyword", "tinee"),
                channels=channels_text,
                autoplay=config.get("autoplay", False),
                volume=config.get("volume", 100)
            ),
            ephemeral=True
        )

    @bot.tree.command(name="set_ai", description="Enable or disable AI replies on this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_ai(interaction: discord.Interaction, enabled: bool):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        config["ai_enabled"] = enabled
        await storage.save_guild_configs()
        await interaction.response.send_message(
            f"AI replies are now {'enabled' if enabled else 'disabled'} for this server.",
            ephemeral=True
        )

    @bot.tree.command(name="set_ai_trigger", description="Sets how AI replies are triggered.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.choices(mode=[
        app_commands.Choice(name="keyword", value="keyword"),
        app_commands.Choice(name="mention", value="mention"),
        app_commands.Choice(name="both", value="both")
    ])
    async def set_ai_trigger(interaction: discord.Interaction, mode: app_commands.Choice[str], keyword: str = None):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        config["ai_trigger"] = mode.value
        if keyword is not None:
            keyword = keyword.strip()
            if keyword:
                config["ai_keyword"] = keyword
        await storage.save_guild_configs()
        await interaction.response.send_message(
            f"AI trigger set to `{mode.value}`.",
            ephemeral=True
        )

    @bot.tree.command(name="set_ai_keyword", description="Sets the keyword that triggers AI replies.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_ai_keyword(interaction: discord.Interaction, keyword: str):
        if await guards.check_command_blocked(interaction):
            return
        keyword = keyword.strip()
        if not keyword:
            await interaction.response.send_message("Keyword cannot be empty.", ephemeral=True)
            return
        config = storage.get_guild_config(interaction.guild.id)
        config["ai_keyword"] = keyword
        await storage.save_guild_configs()
        await interaction.response.send_message(
            f"AI keyword set to `{keyword}`.",
            ephemeral=True
        )

    @bot.tree.command(name="allow_ai_channel", description="Allow AI replies in a specific channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def allow_ai_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        channels = config.get("ai_channels", [])
        if channel.id in channels:
            await interaction.response.send_message(f"{channel.mention} is already allowed.", ephemeral=True)
            return
        channels.append(channel.id)
        config["ai_channels"] = channels
        await storage.save_guild_configs()
        await interaction.response.send_message(
            f"AI replies are now allowed in {channel.mention}.",
            ephemeral=True
        )

    @bot.tree.command(name="block_ai_channel", description="Disallow AI replies in a specific channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def block_ai_channel(interaction: discord.Interaction, channel: discord.TextChannel):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        channels = config.get("ai_channels", [])
        if not channels:
            await interaction.response.send_message(
                "AI is allowed in all channels. Use /allow_ai_channel to set a whitelist first.",
                ephemeral=True
            )
            return
        if channel.id not in channels:
            await interaction.response.send_message(f"{channel.mention} is not in the allow list.", ephemeral=True)
            return
        channels.remove(channel.id)
        config["ai_channels"] = channels
        await storage.save_guild_configs()
        await interaction.response.send_message(
            f"AI replies are now blocked in {channel.mention}.",
            ephemeral=True
        )

    @bot.tree.command(name="clear_ai_channels", description="Allow AI replies in all channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_ai_channels(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        config["ai_channels"] = []
        await storage.save_guild_configs()
        await interaction.response.send_message(
            "AI replies are now allowed in all channels.",
            ephemeral=True
        )

    @sleep.error
    @wake.error
    async def admin_only_error(interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)
