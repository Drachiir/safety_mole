import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
import json
import discord
import discord_timestamps
from discord import app_commands
from discord.ext import commands, tasks
from openai import AsyncOpenAI

import cogs.moderation as modcog
from discord_timestamps import TimestampType
import openai

import time

reported_names = set()
reported_taglines = set()
reported_time = {}
REPORT_TIME_LIMIT = 6000

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class Listener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.messages = dict()
        self.spam_threshold = 5
        self.openai_client: AsyncOpenAI = AsyncOpenAI(api_key=secret_file["openai"])
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.id in [317696057184092171, 331187137758232577, 600398244958437396, 458360424489025539, 752673556017578124]:
            return
        if message.channel.id == secret_file["namereports"]:
            lines = message.content.split("\n")
            if len(lines) < 3:
                return
            username = lines[0].replace("Name:", "").strip()
            tagline = lines[1].replace("Tagline:", "").strip()
            playfab_id = lines[2].replace("PlayFabId:", "").strip()

            current_time = time.time()
            if username in reported_names and (current_time - reported_time.get(username, 0)) < REPORT_TIME_LIMIT:
                if tagline and tagline in reported_taglines and (current_time - reported_time.get(tagline, 0)) < REPORT_TIME_LIMIT:
                    await message.add_reaction("🔁")
                    return
            prompt = (f"Analyze the username '{username}' and tagline '{tagline}' and determine if either contains discriminatory or hateful content, including racism, bigotry, or offensive slurs in English and other languages."
                      f"Be especially vigilant for disguised expressions of hate speech etc."
                      f"General profanity (e.g., 'fuck', 'shit') is acceptable."
                      f"Also look out for player specific callouts in a negative way, e.g Fuck Schakara, Sir3 sucks(Schakara and Sir3 being example playernames), which are not allowed."
                      f"Provide a response in the following format:\n"
                      f"First line: 'True' (if flagged) or 'False' (if not flagged)\n"
                      f"Second line: A short, 28 words max, explanation of the reasoning.")

            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
            except openai.RateLimitError as e:
                print(f"OpenAI Ratelimit: {e}")
                return

            choice = response.choices[0].message.content
            choice_lines = choice.split("\n")
            decision = "true" in choice_lines[0].casefold()

            if decision:
                await message.add_reaction("🤬")
                output_string = (f"{self.bot.user.mention} found a potentially offensive username or tagline:"
                                 f"\n**Username:** '{username}'"
                                 f"\n**Tagline:** '{tagline}'"
                                 f"\n**Kraken:** https://kraken.legiontd2.com/playerid/{playfab_id}"
                                 f"\n**Link:** {message.jump_url}"
                                 f"\n**Reasoning:** {choice_lines[1]}")
                embed = discord.Embed(color=0xDE1919, description=output_string)
                channel_ids = modcog.get_channels(message.guild.id)
                modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
                await modlogs.send(embed=embed)

                reported_names.add(username)
                reported_taglines.add(tagline)
                reported_time[username] = current_time
                reported_time[tagline] = current_time
            else:
                await message.add_reaction("😇")
        if message.guild:
            if message.author.id not in self.messages:
                self.messages[message.author.id] = [message]
            else:
                self.messages[message.author.id].append(message)
                if len(self.messages[message.author.id]) >= self.spam_threshold:
                    channels = set()
                    date_spam = datetime.now(tz=timezone.utc) - timedelta(seconds=50)
                    date_clean = datetime.now(tz=timezone.utc) - timedelta(hours=1)
                    msg: discord.Message
                    for msg in self.messages[message.author.id][:]:
                        if msg.created_at > date_spam:
                            channels.add(msg.channel.name)
                        elif msg.created_at < date_clean:
                            self.messages[message.author.id].remove(msg)
                    if len(channels) >= self.spam_threshold:
                        try:
                            await message.author.timeout(timedelta(days=7), reason="Likely spam bot")
                        except Exception:
                            del self.messages[message.author.id]
                            return
                        output_string = (f"{self.bot.user.mention} detected a spam bot:"
                                         f"\n{message.author.name} (Muted for 7 day)"
                                         f"\n**User id:** {message.author.id}"
                                         f"\n**Deleted messages:**")
                        for msg in self.messages[message.author.id]:
                            d_timestamp = discord_timestamps.format_timestamp(msg.created_at.timestamp(), TimestampType.RELATIVE)
                            output_string += f"\n**Channel: {msg.channel.name}** | {d_timestamp}\n{msg.content}"
                            await msg.delete()
                        embed = discord.Embed(color=0xDE1919, description=output_string)
                        channel_ids = modcog.get_channels(message.guild.id)
                        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
                        await modlogs.send(embed=embed)
                        embed2 = discord.Embed(color=0xDE1919, title=f"You have been muted for spam-bot like behavior. Duration: 7 Days\n"
                                                                     f"If your account was compromised, you may appeal your mute at https://legiontd2.com/bans")
                        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
                        del self.messages[message.author.id]
                        try:
                            await message.author.send(embed=embed2)
                        except Exception:
                            pass
            return

    @commands.Cog.listener()
    async def on_thread_create(self, thread:discord.Thread):
        while not thread.starter_message:
            await asyncio.sleep(0.5)
        if thread.parent.name in ["bugs-and-troubleshooting", "suggestions", "game-balance"]:
            await thread.starter_message.pin()
        for tag in thread.applied_tags:
            if "Bug report" == tag.name:
                break
        else:
            return
        if thread.parent.name == "bugs-and-troubleshooting":
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