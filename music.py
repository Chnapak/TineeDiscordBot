import asyncio

import discord
from discord import FFmpegPCMAudio, PCMVolumeTransformer
import yt_dlp as youtube_dl

import guards
import settings
import state
import storage
import utils


YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
}


def get_guild_volume(guild_id):
    config = storage.get_guild_config(guild_id)
    return config.get("volume", 100)


def build_audio_source(url, guild_id):
    volume = get_guild_volume(guild_id) / 100.0
    source = FFmpegPCMAudio(
        url,
        executable=settings.FFMPEG_PATH,
        before_options=settings.FFMPEG_BEFORE_OPTIONS,
        options=settings.FFMPEG_OPTIONS
    )
    return PCMVolumeTransformer(source, volume=volume)


def get_guild_queue(guild_id):
    if guild_id not in state.song_queues:
        state.song_queues[guild_id] = []
    return state.song_queues[guild_id]


async def youtube_search(query):
    def _extract_info():
        with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
            return ydl.extract_info(f"ytsearch:{query}", download=False)
    return await asyncio.to_thread(_extract_info)


async def get_similar_song(last_song_title):
    try:
        info = await youtube_search(f"{last_song_title} similar songs")
        entries = info.get("entries") if info else []
        if not entries:
            return None, None
        similar_url = entries[0].get("url")
        similar_title = entries[0].get("title")
        return similar_url, similar_title
    except Exception as e:
        print(f"Error fetching similar song: {e}")
        return None, None


async def play_next_song(bot, voice_client, channel, guild_id):
    if not voice_client or not voice_client.is_connected():
        return

    def after_playing(err):
        if err:
            print(f"Error after playing: {err}")
        coro = play_next_song(bot, voice_client, channel, guild_id)
        fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try:
            fut.result()
        except Exception as e:
            print(f"Error in after_playing: {e}")

    queue = get_guild_queue(guild_id)
    if queue:
        url, title = queue.pop(0)
        state.last_song_titles[guild_id] = title
        state.current_tracks[guild_id] = {"title": title, "url": url}
        audio_source = build_audio_source(url, guild_id)

        if voice_client.is_playing():
            voice_client.stop()

        voice_client.play(audio_source, after=after_playing)
        await channel.send(f"Now playing: `{title}`")
    else:
        state.current_tracks.pop(guild_id, None)
        config = storage.get_guild_config(guild_id)
        if not config.get("autoplay", False):
            await channel.send("Queue is empty. Add more songs to the queue!")
            return

        await channel.send("Queue is empty. Searching for a similar song...")
        seed_title = state.last_song_titles.get(guild_id)
        if not seed_title:
            await channel.send("No previous song found. Add more songs to the queue!")
            return
        url, title = await get_similar_song(seed_title)
        if url and title:
            state.last_song_titles[guild_id] = title
            state.current_tracks[guild_id] = {"title": title, "url": url}
            audio_source = build_audio_source(url, guild_id)
            voice_client.play(audio_source, after=after_playing)
            await channel.send(f"Now playing a recommended song: `{title}`")
        else:
            await channel.send("Couldn't find a similar song. Add more songs to the queue!")


def setup(bot):
    @bot.tree.command(name="join", description="Bot joins your current voice channel.")
    async def join(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            if not interaction.guild.voice_client:
                await channel.connect()
                await interaction.response.send_message(f"Joined {channel}")
            else:
                await interaction.response.send_message("I'm already connected to a voice channel.", ephemeral=True)
        else:
            await interaction.response.send_message("You need to be in a voice channel for me to join!", ephemeral=True)

    @bot.tree.command(name="leave", description="Bot leaves the voice channel.")
    async def leave(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        voice_client = interaction.guild.voice_client

        if voice_client:
            await voice_client.disconnect()
            await interaction.response.send_message("Disconnected from the voice channel!")
        else:
            await interaction.response.send_message("I'm not connected to any voice channel!", ephemeral=True)

    @bot.tree.command(name="play", description="Plays a song in the voice channel.")
    async def play(interaction: discord.Interaction, search: str):
        if await guards.check_command_blocked(interaction):
            return

        if not interaction.user.voice:
            await interaction.response.send_message("You need to be in a voice channel for me to join and play music!")
            return

        voice_client = interaction.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            channel = interaction.user.voice.channel
            await channel.connect()
            voice_client = interaction.guild.voice_client

        if not interaction.response.is_done():
            await interaction.response.defer()

        try:
            info = await youtube_search(search)
            entries = info.get("entries") if info else []
            if not entries:
                await interaction.followup.send("Couldn't find the song. Try a different search.")
                return
            url = entries[0].get("url")
            title = entries[0].get("title")
            if not url or not title:
                await interaction.followup.send("Couldn't find the song. Try a different search.")
                return
        except Exception:
            await interaction.followup.send("Couldn't find the song. Try a different search.")
            return

        queue = get_guild_queue(interaction.guild.id)
        queue.append((url, title))
        await interaction.followup.send(f"Added `{title}` to the queue!")

        if not voice_client.is_playing():
            await play_next_song(bot, voice_client, interaction.channel, interaction.guild.id)

    @bot.tree.command(name="pause", description="Pauses the current song.")
    async def pause(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return

        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Playback paused.", ephemeral=True)
        else:
            await interaction.response.send_message("No song is currently playing.", ephemeral=True)

    @bot.tree.command(name="resume", description="Resumes the paused song.")
    async def resume(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return

        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Playback resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("No song is currently paused.", ephemeral=True)

    @bot.tree.command(name="queue", description="Shows the current song queue.")
    async def queue(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return

        queue_items = get_guild_queue(interaction.guild.id)
        if queue_items:
            queue_list = "\n".join([f"{idx + 1}. {title}" for idx, (_, title) in enumerate(queue_items)])
            await interaction.response.send_message(f"Current Queue:\n{queue_list}", ephemeral=True)
        else:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)

    @bot.tree.command(name="nowplaying", description="Shows the currently playing song.")
    async def nowplaying(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return

        voice_client = interaction.guild.voice_client
        track = state.current_tracks.get(interaction.guild.id)
        if voice_client and track and (voice_client.is_playing() or voice_client.is_paused()):
            status = "Paused" if voice_client.is_paused() else "Now playing"
            config = storage.get_guild_config(interaction.guild.id)
            queue_len = len(get_guild_queue(interaction.guild.id))
            embed = discord.Embed(
                title=status,
                description=track["title"],
                color=discord.Color.teal()
            )
            link = utils.build_track_link(track.get("url"))
            if link:
                embed.url = link
            embed.add_field(name="Queue", value=str(queue_len), inline=True)
            embed.add_field(name="Volume", value=f"{config.get('volume', 100)}%", inline=True)
            embed.add_field(name="Autoplay", value="on" if config.get("autoplay", False) else "off", inline=True)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Nothing is currently playing.", ephemeral=True)

    @bot.tree.command(name="volume", description="Sets playback volume (0-200).")
    async def volume(interaction: discord.Interaction, level: int):
        if await guards.check_command_blocked(interaction):
            return
        if level < 0 or level > 200:
            await interaction.response.send_message("Volume must be between 0 and 200.", ephemeral=True)
            return

        config = storage.get_guild_config(interaction.guild.id)
        config["volume"] = level
        await storage.save_guild_configs()

        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.source and hasattr(voice_client.source, "volume"):
            voice_client.source.volume = level / 100.0

        await interaction.response.send_message(f"Volume set to {level}%.", ephemeral=True)

    @bot.tree.command(name="autoplay", description="Enable or disable autoplay when the queue is empty.")
    async def autoplay(interaction: discord.Interaction, enabled: bool):
        if await guards.check_command_blocked(interaction):
            return
        config = storage.get_guild_config(interaction.guild.id)
        config["autoplay"] = enabled
        await storage.save_guild_configs()
        await interaction.response.send_message(
            f"Autoplay is now {'enabled' if enabled else 'disabled'}.",
            ephemeral=True
        )

    @bot.tree.command(name="remove", description="Removes a song from the queue by position.")
    async def remove(interaction: discord.Interaction, position: int):
        if await guards.check_command_blocked(interaction):
            return

        queue_items = get_guild_queue(interaction.guild.id)
        if not queue_items:
            await interaction.response.send_message("The queue is empty.", ephemeral=True)
            return
        index = position - 1
        if index < 0 or index >= len(queue_items):
            await interaction.response.send_message("Invalid queue position.", ephemeral=True)
            return
        _, title = queue_items.pop(index)
        await interaction.response.send_message(f"Removed `{title}` from the queue.", ephemeral=True)

    @bot.tree.command(name="clear", description="Clears the song queue.")
    async def clear(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return
        queue_items = get_guild_queue(interaction.guild.id)
        if queue_items:
            queue_items.clear()
            await interaction.response.send_message("Cleared the queue.", ephemeral=True)
        else:
            await interaction.response.send_message("The queue is already empty.", ephemeral=True)

    @bot.tree.command(name="skip", description="Skips the currently playing song.")
    async def skip(interaction: discord.Interaction):
        if await guards.check_command_blocked(interaction):
            return

        voice_client = interaction.guild.voice_client

        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Skipped the current song!")
        else:
            await interaction.response.send_message("No song is currently playing to skip.", ephemeral=True)
