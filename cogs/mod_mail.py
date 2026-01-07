import asyncio
import os
import json
import pathlib
import traceback
from datetime import datetime, timedelta, timezone
import aiosqlite
import discord
from discord.ext import commands
import cogs.moderation as modcog
import aiohttp

DB_PATH = os.path.join("Files", "modmail_threads.db")


async def send_webhook_message(forum_channel: discord.ForumChannel, thread: discord.Thread, user: discord.User, content: str, files=None):
    """Send a message inside a thread using the main webhook of the forum channel.
    Returns the webhook message ID if successful, None otherwise."""

    webhooks = await forum_channel.webhooks()
    webhook = webhooks[0] if webhooks else await forum_channel.create_webhook(name="ModMail Webhook")

    if not content and not files:
        return None

    payload = {
        "username": user.display_name,  # Mimic user
        "avatar_url": user.avatar.url if user.avatar else user.default_avatar.url,  # Use user's avatar
        "content": content
    }

    headers = {
        "Content-Type": "application/json"
    }

    webhook_url = webhook.url
    async with aiohttp.ClientSession() as session:
        # Add wait=true to get the message object back
        async with session.post(webhook_url, json=payload, headers=headers, params={"thread_id": thread.id, "wait": "true"}) as response:
            if response.status not in (200, 204):
                error_text = await response.text()
                print(f"⚠️ Webhook Error: {response.status} - {error_text}")
                return None
            if response.status == 200:
                data = await response.json()
                return data.get("id")
    return None


async def edit_webhook_message(forum_channel: discord.ForumChannel, thread: discord.Thread, message_id: str, new_content: str):
    """Edit a webhook message in a thread."""
    webhooks = await forum_channel.webhooks()
    webhook = webhooks[0] if webhooks else None
    if not webhook:
        return False

    payload = {"content": new_content}
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        url = f"{webhook.url}/messages/{message_id}"
        async with session.patch(url, json=payload, headers=headers, params={"thread_id": thread.id}) as response:
            return response.status == 200


async def delete_webhook_message(forum_channel: discord.ForumChannel, thread: discord.Thread, message_id: str):
    """Delete a webhook message in a thread."""
    webhooks = await forum_channel.webhooks()
    webhook = webhooks[0] if webhooks else None
    if not webhook:
        return False

    async with aiohttp.ClientSession() as session:
        url = f"{webhook.url}/messages/{message_id}"
        async with session.delete(url, params={"thread_id": thread.id}) as response:
            return response.status == 204


class ConfirmSupportView(discord.ui.View):
    def __init__(self, author: discord.User, on_timeout_callback=None, timeout=180):
        super().__init__(timeout=timeout)
        self.author = author
        self.message = None  # Ensure attribute always exists
        self.confirmed = asyncio.Event()
        self.on_timeout_callback = on_timeout_callback  # Cleanup handler

    @discord.ui.button(label="Contact Support", style=discord.ButtonStyle.green, custom_id="confirm_support")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This isn't your confirmation button!", ephemeral=True)
            return

        if self.message:
            try:
                await self.message.delete()
            except discord.HTTPException:
                pass

        self.confirmed.set()
        self.stop()

    async def on_timeout(self):
        # Called when the view times out
        try:
            if self.message:
                await self.message.edit(content="⏰ Confirmation timed out. Please send a new message to try again.", view=None)
        except Exception:
            pass

        if self.on_timeout_callback:
            await self.on_timeout_callback(self.author.id)

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modmail_threads (
                user_id TEXT PRIMARY KEY,
                thread_id TEXT
            )
        """)
        # Table to track message mappings for edit/delete support (staff -> user DMs)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modmail_messages (
                thread_message_id TEXT PRIMARY KEY,
                dm_message_id TEXT,
                user_id TEXT
            )
        """)
        # Table to track user DM -> webhook message mappings (user DMs -> forum)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modmail_user_messages (
                dm_message_id TEXT PRIMARY KEY,
                webhook_message_id TEXT,
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


async def save_message_mapping(thread_message_id, dm_message_id, user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("REPLACE INTO modmail_messages (thread_message_id, dm_message_id, user_id) VALUES (?, ?, ?)",
                         (str(thread_message_id), str(dm_message_id), str(user_id)))
        await db.commit()


async def get_message_mapping(thread_message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT dm_message_id, user_id FROM modmail_messages WHERE thread_message_id = ?",
                              (str(thread_message_id),)) as cursor:
            result = await cursor.fetchone()
            return result if result else None


async def delete_message_mapping(thread_message_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM modmail_messages WHERE thread_message_id = ?", (str(thread_message_id),))
        await db.commit()


async def save_user_message_mapping(dm_message_id, webhook_message_id, thread_id):
    """Save mapping from user's DM message to webhook message in forum."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("REPLACE INTO modmail_user_messages (dm_message_id, webhook_message_id, thread_id) VALUES (?, ?, ?)",
                         (str(dm_message_id), str(webhook_message_id), str(thread_id)))
        await db.commit()


async def get_user_message_mapping(dm_message_id):
    """Get webhook message ID and thread ID from user's DM message ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT webhook_message_id, thread_id FROM modmail_user_messages WHERE dm_message_id = ?",
                              (str(dm_message_id),)) as cursor:
            result = await cursor.fetchone()
            return result if result else None


async def delete_user_message_mapping(dm_message_id):
    """Delete mapping for a user's DM message."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM modmail_user_messages WHERE dm_message_id = ?", (str(dm_message_id),))
        await db.commit()


class ModMail(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = str(pathlib.Path(__file__).parent.parent.resolve()) + "/user_data.db"
        self.pending_confirmations = set()  # Track users mid-confirmation

    async def cleanup_confirmation(self, user_id):
        self.pending_confirmations.discard(user_id)

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
            # This is a DM message from a user, check if banned
            json_file_path = os.path.join("Files", "banned_users.json")
            if os.path.exists(json_file_path):
                with open(json_file_path, "r") as file:
                    banned_users = json.load(file)
                user_id = str(message.author.id)
                if user_id in banned_users:
                    unban_time = datetime.fromisoformat(banned_users[user_id]["unban_time"])
                    now = datetime.now(timezone.utc)

                    if now >= unban_time:
                        # Ban expired, remove user from the JSON
                        del banned_users[user_id]
                        with open(json_file_path, "w") as file:
                            json.dump(banned_users, file, indent=4)
                    else:
                        await message.channel.send("You are banned from using Support requests ❌")
                        return

            if message.author.id in self.pending_confirmations:
                return

            guild = self.bot.get_guild(self.bot.guild_id)
            channel_ids = modcog.get_channels(self.bot.guild_id)
            forum_channel: discord.ForumChannel = self.bot.get_channel(channel_ids["mod_mail"])
            existing_thread_id = await get_thread_id(message.author.id)
            thread = None
            files = [await att.to_file() for att in message.attachments]

            if existing_thread_id:
                try:
                    thread = await guild.fetch_channel(existing_thread_id)
                    if not thread:
                        thread = None
                    elif thread.locked or thread.archived:
                        thread = None
                except Exception:
                    thread = None
            try:
                if not thread:
                    self.pending_confirmations.add(message.author.id)
                    view = ConfirmSupportView(
                        author=message.author,
                        on_timeout_callback=self.cleanup_confirmation
                    )
                    confirm_message = await message.channel.send(
                        "👋 Hello! Please confirm you wish to contact the Support team by clicking the button below:",
                        view=view
                    )
                    view.message = confirm_message  # Assign after send
                    try:
                        await view.confirmed.wait()
                    except asyncio.TimeoutError:
                        await message.channel.send("⏰ You didn't confirm in time. Please try again if you still need help.")
                    finally:
                        self.pending_confirmations.discard(message.author.id)

                    await message.channel.send("✅ Your request has been sent to the Support team. (Expected response time <24h, but can take longer)"
                                               "\n⚠️ Please make sure to have DMs enabled to receive a response."
                                               "\n📨 Messages are marked with ✅ if they were sent to the support team."
                                               "\n📃 Responses will appear here, you can add additional messages:")
                    # Find "In Progress" tag to apply to new threads
                    applied_tags = [tag for tag in forum_channel.available_tags if tag.name == "In Progress"]
                    thread = await forum_channel.create_thread(name=f"Support Request - {message.author.display_name} / {message.author.name}",
                                                               auto_archive_duration=1440, 
                                                               applied_tags=applied_tags,
                                                               content=f"Support Request - {message.author.display_name} / {message.author.name} / {message.author.id}\n"
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
                    webhook_msg_id = await send_webhook_message(forum_channel, thread.thread, message.author, message.content)
                    if webhook_msg_id:
                        await save_user_message_mapping(message.id, webhook_msg_id, thread.thread.id)
                    if files:
                        await thread.thread.send(files=files)
                else:
                    webhook_msg_id = await send_webhook_message(forum_channel, thread, message.author, message.content)
                    if webhook_msg_id:
                        await save_user_message_mapping(message.id, webhook_msg_id, thread.id)
                    if files:
                        await thread.send(files=files)
                await message.add_reaction("✅")
            except Exception:
                traceback.print_exc()
                await message.add_reaction("❌")
                await message.author.send("Something went wrong sending this message, please try again.")

        elif isinstance(message.channel, discord.Thread):
            # This is a message inside a thread in the forum
            if message.content.startswith("?") or message.content.startswith("!"):
                return
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id FROM modmail_threads WHERE thread_id = ?", (str(message.channel.id),)) as cursor:
                    result = await cursor.fetchone()
                    if result:
                        user_id = int(result[0])
                        user = await self.bot.fetch_user(user_id)
                        if user:
                            try:
                                files = [await att.to_file() for att in message.attachments]
                                dm_message = await user.send(f"{message.content}", files=files)
                                # Save mapping for edit/delete support
                                await save_message_mapping(message.id, dm_message.id, user_id)
                                await message.add_reaction("✅")
                            except Exception:
                                traceback.print_exc()
                                await message.channel.send("It seems that the user has DM's disabled...")
                                await message.add_reaction("❌")
                                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Mirror message deletions."""
        if message.author.bot:
            return
        
        # Case 1: Message deleted in forum thread -> delete from user's DMs
        if isinstance(message.channel, discord.Thread):
            mapping = await get_message_mapping(message.id)
            if not mapping:
                return
            
            dm_message_id, user_id = mapping
            try:
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    dm_channel = await user.create_dm()
                    dm_message = await dm_channel.fetch_message(int(dm_message_id))
                    await dm_message.delete()
            except discord.NotFound:
                pass  # Message already deleted
            except Exception:
                traceback.print_exc()
            finally:
                await delete_message_mapping(message.id)
        
        # Case 2: Message deleted in user's DMs -> delete webhook message from forum
        elif message.guild is None:
            mapping = await get_user_message_mapping(message.id)
            if not mapping:
                return
            
            webhook_message_id, thread_id = mapping
            try:
                guild = self.bot.get_guild(self.bot.guild_id)
                channel_ids = modcog.get_channels(self.bot.guild_id)
                forum_channel: discord.ForumChannel = self.bot.get_channel(channel_ids["mod_mail"])
                thread = await guild.fetch_channel(int(thread_id))
                if thread and forum_channel:
                    await delete_webhook_message(forum_channel, thread, webhook_message_id)
            except Exception:
                traceback.print_exc()
            finally:
                await delete_user_message_mapping(message.id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Mirror message edits."""
        if after.author.bot:
            return
        if before.content == after.content:
            return  # No actual content change
        
        # Case 1: Message edited in forum thread -> edit in user's DMs
        if isinstance(after.channel, discord.Thread):
            mapping = await get_message_mapping(after.id)
            if not mapping:
                return
            
            dm_message_id, user_id = mapping
            try:
                user = await self.bot.fetch_user(int(user_id))
                if user:
                    dm_channel = await user.create_dm()
                    dm_message = await dm_channel.fetch_message(int(dm_message_id))
                    await dm_message.edit(content=after.content)
            except discord.NotFound:
                await delete_message_mapping(after.id)
            except Exception:
                traceback.print_exc()
        
        # Case 2: Message edited in user's DMs -> edit webhook message in forum
        elif after.guild is None:
            mapping = await get_user_message_mapping(after.id)
            if not mapping:
                return
            
            webhook_message_id, thread_id = mapping
            try:
                guild = self.bot.get_guild(self.bot.guild_id)
                channel_ids = modcog.get_channels(self.bot.guild_id)
                forum_channel: discord.ForumChannel = self.bot.get_channel(channel_ids["mod_mail"])
                thread = await guild.fetch_channel(int(thread_id))
                if thread and forum_channel:
                    await edit_webhook_message(forum_channel, thread, webhook_message_id, after.content)
            except Exception:
                traceback.print_exc()


async def setup(bot:commands.Bot):
    await bot.add_cog(ModMail(bot))
