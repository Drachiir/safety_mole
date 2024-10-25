import pathlib
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
import random
import string
from datetime import datetime, timedelta, timezone
import asyncio
import json

with open(str(pathlib.Path(__file__).parent.parent.resolve()) + "/Files/json/rank_roles.json", "r") as config_file:
    config = json.load(config_file)

GUILD_ID = config["GUILD_ID"]
GLOBAL_CHAT_CHANNEL_ID = config["GLOBAL_CHAT_CHANNEL_ID"]
RANK_ROLES = {rank: int(role_id) for rank, role_id in config["RANK_ROLES"].items()}
DB_PATH = str(pathlib.Path(__file__).parent.parent.resolve()) + config["DB_PATH"]


class GameAuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = DB_PATH
        self.global_chat_id = GLOBAL_CHAT_CHANNEL_ID
        self.rank_roles = RANK_ROLES
        self.auth_requests = {}
        self.bot.loop.create_task(self.create_db())
    
    async def create_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id TEXT PRIMARY KEY,
                    player_id TEXT,
                    rank TEXT
                )
            """)
            await db.commit()
    
    @app_commands.command(name="rank_role", description="Start authentication process to get a rank badge.")
    async def rank_role(self, interaction: discord.Interaction):
        await interaction.defer()
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6)) + "(Do not copy/paste this unless you know why)"
        self.auth_requests[interaction.user.id] = {
            "code": code,
            "expires": datetime.now(tz=timezone.utc) + timedelta(minutes=10),
            "user": interaction.user,
            "channel": interaction.channel,
        }
        
        await interaction.followup.send(
            f"Please post this code in the global chat *IN-GAME* within the next 10 minutes to authenticate:\n`{code}`",
            ephemeral=True
        )
        self.check_auth_requests.start()
    
    @tasks.loop(seconds=5)
    async def check_auth_requests(self):
        now = datetime.now(tz=timezone.utc)
        for user_id, auth_data in list(self.auth_requests.items()):
            if now > auth_data["expires"]:
                await auth_data["user"].send(
                    f"<@{user_id}>, authentication timed out. Please try again using /rank."
                )
                del self.auth_requests[user_id]
        
        channel = self.bot.get_channel(self.global_chat_id)
        async for message in channel.history(limit=50):
            if not message.webhook_id or not message.author.name.endswith("[Game Chat]"):
                continue
            
            user_id, code, found = None, None, False
            for user_id, auth_data in self.auth_requests.items():
                if auth_data["code"] in message.content:
                    code = auth_data["code"]
                    found = True
                    break
            if found:
                await self.process_authentication(message.author, user_id, code)
                await message.delete()
                break
    
    async def process_authentication(self, game_user, discord_user_id, code):
        player_id = "12345"  # Placeholder, replace with actual API call
        rank = "Legend"  # Placeholder, replace with actual API call
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (discord_id, player_id, rank)
                VALUES (?, ?, ?)
            """, (discord_user_id, player_id, rank))
            await db.commit()
        
        discord_user = await self.bot.fetch_user(discord_user_id)
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(discord_user_id)
        rank_role_id = self.rank_roles.get(rank)
        if rank_role_id:
            rank_role = guild.get_role(rank_role_id)
            await member.add_roles(rank_role)
            await discord_user.send(f"Authentication successful! You have been assigned the rank: {rank}")
        
        del self.auth_requests[discord_user_id]
    
    @app_commands.command(name="update-rank", description="Update your rank badge.")
    async def update_rank(self, interaction: discord.Interaction):
        await interaction.defer()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT player_id FROM users WHERE discord_id = ?", (str(interaction.user.id),)) as cursor:
                result = await cursor.fetchone()
        
        if not result:
            await interaction.followup.send("You need to authenticate first using /rank.", ephemeral=True)
            return
        
        player_id = result[0]
    
        rank = "Legend"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET rank = ? WHERE discord_id = ?", (rank, str(interaction.user.id)))
            await db.commit()
        
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_user(interaction.user.id)
        
        for role_name, role_id in self.rank_roles.items():
            role = guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
        
        new_rank_role = guild.get_role(self.rank_roles[rank])
        await member.add_roles(new_rank_role)
        await interaction.followup.send(f"Your rank has been updated to: {rank}", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(GameAuthCog(bot))
