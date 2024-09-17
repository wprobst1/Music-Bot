import os
from typing import Final
from dotenv import load_dotenv
from discord import Intents, Message
from discord.ext import commands
import yt_dlp
import discord
import asyncio

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

intents: Intents = Intents.default()
intents.message_content = True
intents.voice_states = True

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': True}

class MusicBot(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("You are not in a voice channel.")
        if not ctx.voice_client:
            await voice_channel.connect()
        
        async with ctx.typing():
            try:
                with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                    info = ydl.extract_info(f"ytsearch:{search}", download=False)
                    if 'entries' in info:
                        info = info['entries'][0]
                    url = info.get('url')
                    title = info.get('title')
                    self.queue.append((url, title))
                    await ctx.send(f"Added to queue: **{title}**")
                    if not ctx.voice_client.is_playing():
                        await self.play_next(ctx)
            except Exception as e:
                await ctx.send(f"An error occurred: {str(e)}")
                print("Error in play command:", e)

    async def play_next(self, ctx):
        if self.queue:
            url, title = self.queue.pop(0)         
            try:
                source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
                ctx.voice_client.play(source, after=lambda _: self.client.loop.create_task(self.play_next(ctx)))
                await ctx.send(f'Now playing **{title}**')
            except Exception as e:
                print(f"Error playing audio: {e}")
                await ctx.send(f"Could not play the song: {str(e)}")
        else:
            await ctx.send("Queue is empty.")
            if ctx.voice_client.is_connected():
                await ctx.voice_client.disconnect()

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Song skipped.")
        else:
            await ctx.send("No song to skip.")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            self.is_paused = True
            await ctx.send("Song paused.")
        else:
            await ctx.send("No song to pause.")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.resume()
            self.is_paused = False
            await ctx.send("Song resumed.")
        else:
            await ctx.send("No song to resume.")

client = commands.Bot(command_prefix="!", intents=intents)

@client.event
async def on_ready() -> None:
    print(f'{client.user} is now running.')

async def main():
    await client.add_cog(MusicBot(client))
    await client.start(TOKEN)

asyncio.run(main())
