import json
import discord
from discord import app_commands
from discord.ext import commands

class Listener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread:discord.Thread):
        if thread.parent.name == "bugs-and-troubleshooting":
            await thread.send(f"Please make sure your post follows the guidelines\nhttps://discord.com/channels/159363816570880012/1064534565386985513/1064534565386985513")

async def setup(bot:commands.Bot):
    await bot.add_cog(Listener(bot))