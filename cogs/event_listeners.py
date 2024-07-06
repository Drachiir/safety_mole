import asyncio
from datetime import datetime, timedelta, timezone
import json
import discord
import discord_timestamps
from discord import app_commands
from discord.ext import commands, tasks
import cogs.moderation as modcog
from discord_timestamps import TimestampType

class Listener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.messages = dict()
        self.spam_threshold = 6
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        if message.guild:
            if message.author.id not in self.messages:
                self.messages[message.author.id] = [message]
            else:
                self.messages[message.author.id].append(message)
                if len(self.messages[message.author.id]) >= self.spam_threshold:
                    channels = set()
                    date_spam = datetime.now(tz=timezone.utc) - timedelta(seconds=20)
                    spam_count = 0
                    msg: discord.Message
                    for i, msg in enumerate(self.messages[message.author.id][:]):
                        if msg.created_at > date_spam:
                            channels.add(msg.channel.name)
                            spam_count += 1
                        else:
                            self.messages[message.author.id].pop(i)
                            continue
                    if spam_count >= self.spam_threshold and len(channels) >= self.spam_threshold:
                        await message.author.timeout(timedelta(days=1), reason="Likely spam bot")
                        output_string = (f"{self.bot.user.mention} detected a likely spam bot:"
                                         f"\n{message.author.mention} (Muted for 1 day)"
                                         f"\n**Deleted messages:**")
                        for msg in self.messages[message.author.id]:
                            d_timestamp = discord_timestamps.format_timestamp(msg.created_at.timestamp(), TimestampType.RELATIVE)
                            output_string += f"\nMessage in {msg.channel.name} at {d_timestamp}\n{msg.content}"
                            await msg.delete()
                        embed = discord.Embed(color=0xDE1919, description=output_string)
                        channel_ids = modcog.get_channels(message.guild.id)
                        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
                        await modlogs.send(embed=embed)
                        embed2 = discord.Embed(color=0xDE1919, title=f"You have been muted for spam-bot like behavior.\nDuration: 1 Day")
                        del self.messages[message.author.id]
                        try:
                            await message.author.send(embed=embed2)
                        except Exception:
                            pass
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