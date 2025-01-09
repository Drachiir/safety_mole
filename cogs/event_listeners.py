import asyncio
import os
from datetime import datetime, timedelta, timezone
import json
import discord
import discord_timestamps
from discord import app_commands
from discord.ext import commands, tasks
import cogs.moderation as modcog
from discord_timestamps import TimestampType
from discord.ui import Button, View, Modal, TextInput

PERSISTENT_VIEW_FILE = "persistent_views.json"

class ReplyModal(Modal):
    def __init__(self, author_id, button, view):
        super().__init__(title="Reply to User")
        self.author_id = author_id
        self.button = button
        self.view = view
        self.reply_content = TextInput(label="Reply Message", style=discord.TextStyle.long, required=True)
        self.add_item(self.reply_content)

    async def on_submit(self, interaction: discord.Interaction):
        self.button.disabled = False
        await interaction.message.edit(view=self.view)

        user = await interaction.client.fetch_user(self.author_id)
        await user.send(f"{self.reply_content.value}")

        embed = discord.Embed(
            color=0xDE1919,
            description=f"**{interaction.user.mention}** replied to {user.mention}."
                        f"\n**Message Content:**\n{self.reply_content.value}"
        )
        await interaction.response.send_message(embed=embed)

    async def on_error(self, error, interaction):
        self.button.disabled = False
        await interaction.message.edit(view=self.view)
        raise error

class ReplyButton(Button):
    def __init__(self, author_id, view):
        super().__init__(label="Reply", style=discord.ButtonStyle.primary, custom_id=f"reply_button_{author_id}")
        self.author_id = author_id
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await interaction.message.edit(view=self.parent_view)

        modal = ReplyModal(author_id=self.author_id, button=self, view=self.parent_view)
        await interaction.response.send_modal(modal)

        await asyncio.sleep(120)
        self.disabled = False
        await interaction.message.edit(view=self.parent_view)


class ModMailView(View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        reply_button = ReplyButton(author_id=author_id, view=self)
        self.add_item(reply_button)

def save_persistent_view(user_id):
    if not os.path.exists(PERSISTENT_VIEW_FILE):
        with open(PERSISTENT_VIEW_FILE, "w") as file:
            json.dump([], file)

    with open(PERSISTENT_VIEW_FILE, "r") as file:
        data = json.load(file)

    if user_id not in data:
        data.append(user_id)
        with open(PERSISTENT_VIEW_FILE, "w") as file:
            json.dump(data, file)

class Listener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.messages = dict()
        self.spam_threshold = 5
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        if message.channel.id in [317696057184092171, 331187137758232577, 600398244958437396, 458360424489025539, 752673556017578124]:
            return
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
                                         f"\n{message.author.mention} (Muted for 7 day)"
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
        else:
            if message.author.bot or message.content == "?sync":
                return

            json_file_path = os.path.join("Files", "banned_users.json")
            if os.path.exists(json_file_path):
                with open(json_file_path, "r") as file:
                    banned_users = json.load(file)
                if str(message.author.id) in banned_users:
                    await message.channel.send("You are banned from using Mod Mail ❌")
                    return

            channel_ids = modcog.get_channels(self.bot.guild_id)
            modmail = await self.bot.fetch_channel(channel_ids["mod_mail"])

            embed = discord.Embed(
                color=0xDE1919,
                description=f"**{message.author.mention} ({message.author.name})** sent a message."
                            f"\n**Message Date:** {message.created_at.strftime('%d/%m/%Y, %H:%M:%S')}"
                            f"\n**Message Content:**\n{message.content}"
                            f"{'\n**Attachments:**' if message.attachments else ''}"
            )

            view = ModMailView(author_id=message.author.id)
            save_persistent_view(message.author.id)

            files = []
            if message.attachments:
                for i, att in enumerate(message.attachments):
                    files.append(await att.to_file(filename=att.filename))
                if len(files) == 1 and files[0].filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
                    embed.set_image(url=f"attachment://{files[0].filename}")
                    await modmail.send(embed=embed, file=files[0], view=view)
                else:
                    await modmail.send(embed=embed, view=view)
                    await modmail.send(files=files)
            else:
                await modmail.send(embed=embed, view=view)

            await message.channel.send("Your message has been sent to the Moderation team ✅")

    @commands.Cog.listener()
    async def on_thread_create(self, thread:discord.Thread):
        while not thread.starter_message:
            await asyncio.sleep(0.5)
        if thread.parent.name in ["bugs-and-troubleshooting", "suggestions"]:
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

async def setup_persistent_views(bot):
    if os.path.exists(PERSISTENT_VIEW_FILE):
        with open(PERSISTENT_VIEW_FILE, "r") as file:
            user_ids = json.load(file)

        for user_id in user_ids:
            bot.add_view(ModMailView(author_id=user_id))

async def setup(bot:commands.Bot):
    await bot.add_cog(Listener(bot))