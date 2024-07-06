import asyncio
from datetime import datetime, timedelta, timezone
import json
import discord
from discord import app_commands
from discord.ext import commands, tasks

class Listener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.messages = dict()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        if message.guild:
            # if message.author.id not in self.messages:
            #     self.messages[message.author.id] = [message]
            # else:
            #     self.messages[message.author.id].append(message)
            #     if len(self.messages[message.author.id]) > 1:
            #         date_spam = datetime.now(tz=timezone.utc) - timedelta(seconds=10)
            #         spam_count = 0
            #         msg: discord.Message
            #         for i, msg in enumerate(self.messages[message.author.id][:]):
            #             if msg.created_at > date_spam:
            #                 spam_count += 1
            #                 await message.channel.send("spam")
            #             else:
            #                 self.messages[message.author.id].pop(i)
            #                 continue
            #             print(self.messages[message.author.id])
            return
        else:
            await message.channel.send("This Bot does not accept messages. For ban appeals please visit https://legiontd2.com/bans")
            return
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread:discord.Thread):
        if thread.parent.name == "bugs-and-troubleshooting":
            while not thread.starter_message:
                await asyncio.sleep(1)
            for tag in thread.applied_tags:
                if "Bug report" == tag.name:
                    break
            else:
                return
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