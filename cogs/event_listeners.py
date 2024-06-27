import asyncio
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
            while not thread.starter_message:
                await asyncio.sleep(1)
            message = thread.starter_message
            if not message.attachments:
                await thread.send(f"Thanks for submitting a bug-report {thread.owner.mention}\n"
                                  f"You have not attached any files.\nIn order to help you, we may need Log files and/or Screenshots/Video(s) of the bug happening.\n"
                                  f"Please check out the bug-report guidelines: https://discord.com/channels/159363816570880012/1064534565386985513/1064534565386985513")
            else:
                await thread.send(f"Thanks for submitting a bug-report {thread.owner.mention}\n"
                                  f"Please make sure your post follows the guidelines, if you haven't already\nhttps://discord.com/channels/159363816570880012/1064534565386985513/1064534565386985513")

async def setup(bot:commands.Bot):
    await bot.add_cog(Listener(bot))