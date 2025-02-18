import asyncio
import os
import json
import aiosqlite
import discord
from discord.ext import commands
import cogs.moderation as modcog
import aiohttp

DB_PATH = os.path.join("Files", "modmail_threads.db")


async def send_webhook_message(forum_channel: discord.ForumChannel, thread: discord.Thread, user: discord.User, content: str, files=None):
    """Send a message inside a thread using the main webhook of the forum channel."""

    webhooks = await forum_channel.webhooks()
    webhook = webhooks[0] if webhooks else await forum_channel.create_webhook(name="ModMail Webhook")

    if not content and not files:
        return

    payload = {
        "username": user.display_name,  # Mimic user
        "avatar_url": user.avatar.url if user.avatar else user.default_avatar.url,  # Use user’s avatar
        "content": content
    }

    headers = {
        "Content-Type": "application/json"
    }

    webhook_url = webhook.url
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload, headers=headers, params={"thread_id": thread.id}) as response:
            if response.status != 204 and response.status != 200:
                error_text = await response.text()
                print(f"⚠️ Webhook Error: {response.status} - {error_text}")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modmail_threads (
                user_id TEXT PRIMARY KEY,
                thread_id TEXT
            )
        """)
        await db.commit()


async def get_thread_id(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT thread_id FROM modmail_threads WHERE user_id = ?", (str(user_id),)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else None


async def save_thread_id(user_id, thread_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("REPLACE INTO modmail_threads (user_id, thread_id) VALUES (?, ?)", (str(user_id), str(thread_id)))
        await db.commit()


class ModMail(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "/user_data.db"

    @commands.Cog.listener()
    async def on_ready(self):
        await init_db()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.author.name == "drachir_" and message.content.startswith("?"):
            return

        if message.guild is None:
            # This is a DM message from a user
            json_file_path = os.path.join("Files", "banned_users.json")
            if os.path.exists(json_file_path):
                with open(json_file_path, "r") as file:
                    banned_users = json.load(file)
                if str(message.author.id) in banned_users:
                    await message.channel.send("You are banned from using Support requests ❌")
                    return

            guild = self.bot.get_guild(self.bot.guild_id)
            channel_ids = modcog.get_channels(self.bot.guild_id)
            forum_channel: discord.ForumChannel = self.bot.get_channel(channel_ids["mod_mail"])
            existing_thread_id = await get_thread_id(message.author.id)
            thread = None
            files = [await att.to_file() for att in message.attachments]

            if existing_thread_id:
                thread = await guild.fetch_channel(existing_thread_id)
                if thread and "done" in [tag.name.lower() for tag in thread.applied_tags]:
                    thread = None  # Create a new one if the old one is marked as done
            try:
                if not thread:
                    await message.channel.send("✅ Your request has been sent to the Support team. (Expected response time <24h, but can take longer)"
                                               "\n⚠️ Please make sure to have DMs enabled to receive a response."
                                               "\n📃 Responses will appear here:")
                    thread = await forum_channel.create_thread(name=f"Support Request - {message.author.display_name} / {message.author.name}",
                                                               auto_archive_duration=1440, content=f"Support Request - {message.author.display_name} / {message.author.name} / {message.author.id}\n"
                                                                                                   f"Replies to this thread will be relayed to the user. Marked with ✅ if successful.")
                    await save_thread_id(message.author.id, thread.thread.id)
                    # GET GAME ACCOUNT IF LINKED
                    async with aiosqlite.connect(self.db_path) as db:
                        async with db.execute("SELECT player_id, ingame_name FROM users WHERE discord_id = ?", (str(message.author.id),)) as cursor:
                            result = await cursor.fetchone()
                    if result:
                        await thread.thread.send(f"**Game Account Name**: {result[1]}\n"
                                                 f"**Kraken:** https://kraken.legiontd2.com/playerid/{result[0]}")
                    # SEND WEBHOOK USING USER AVATAR AND NAME
                    await send_webhook_message(forum_channel, thread.thread, message.author, message.content)
                    if files:
                        await thread.thread.send(files=files)
                else:
                    await send_webhook_message(forum_channel, thread, message.author, message.content)
                    if files:
                        await thread.send(files=files)
                await message.add_reaction("✅")
            except Exception:
                await message.add_reaction("❌")
                await message.author.send("Something went wrong sending this message, please try again.")

        elif isinstance(message.channel, discord.Thread):
            # This is a message inside a thread in the forum
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id FROM modmail_threads WHERE thread_id = ?", (str(message.channel.id),)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        user_id = int(result[0])
                        user = await self.bot.fetch_user(user_id)
                        if user:
                            try:
                                files = [await att.to_file() for att in message.attachments]
                                await user.send(f"{message.content}", files=files)
                                await message.add_reaction("✅")
                            except Exception:
                                await message.channel.send("It seems that the user has DM's disabled...")
                                await message.add_reaction("❌")
                                pass


async def setup(bot:commands.Bot):
    await bot.add_cog(ModMail(bot))