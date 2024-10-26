import pathlib
import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
import aiohttp
import random
import string
from datetime import datetime, timedelta, timezone
import asyncio
import json

with open("Files/json/rank_roles.json", "r") as config_file:
    config = json.load(config_file)

with open("Files/json/Secrets.json", "r") as secret_file:
    secret = json.load(secret_file)

def get_channels(guild_id):
    try:
        with open(f"Files/Config/{guild_id}.json", "r") as f:
            return json.load(f)
    except Exception:
        return None

GUILD_ID = config["GUILD_ID"]
GLOBAL_CHAT_CHANNEL_ID = config["GLOBAL_CHAT_CHANNEL_ID"]
RANK_ROLES = {rank: int(role_id) for rank, role_id in config["RANK_ROLES"].items()}
DB_PATH = str(pathlib.Path(__file__).parent.parent.resolve()) + config["DB_PATH"]

def get_rank_name(elo):
    ranks = {
        2800: 'Legend',
        2600: 'Grandmaster',
        2400: 'SeniorMaster',
        2200: 'Master',
        2000: 'Expert',
        1800: 'Diamond',
        1600: 'Platinum',
        1400: 'Gold',
        1200: 'Silver',
        1000: 'Bronze',
    }
    for threshold, rank in ranks.items():
        if elo >= threshold:
            return rank
    return 'Unranked'

rank_emotes = {
    "Unranked": "<:Unranked:1241064654717980723>",
    "Bronze": "<:Bronze:1217999684484862057>",
    "Silver": "<:Silver:1217999706555158631>",
    "Gold": "<:Gold:1217999690369335407>",
    "Platinum": "<:Platinum:1217999701337571379>",
    "Diamond": "<:Diamond:1217999686888325150>",
    "Expert": "<:Expert:1217999688494747718>",
    "Master": "<:Master:1217999699114590248>",
    "SeniorMaster": "<:SeniorMaster:1217999704349081701>",
    "Grandmaster": "<:Grandmaster:1217999691883741224>",
    "Legend": "<:Legend:1217999693234176050>"
}


class GameAuthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
        self.guild_id = GUILD_ID
        self.global_chat_id = GLOBAL_CHAT_CHANNEL_ID
        self.rank_roles = RANK_ROLES
        self.auth_requests = {}
        self.session = aiohttp.ClientSession(headers={'x-api-key': secret.get('apikey')})
        self.bot.loop.create_task(self.create_db())
    
    async def create_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id TEXT PRIMARY KEY,
                    player_id TEXT UNIQUE,
                    rank TEXT
                )
            """)
            await db.commit()
    
    async def cog_unload(self):
        await self.session.close()
    
    @app_commands.command(name="rank", description="Start authentication process to get a rank badge.")
    async def rank_role(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        code = "/" + (''.join(random.choices(string.ascii_uppercase + string.digits, k=8))) #+ "(Do not copy/paste this unless you know why)"
        self.auth_requests[interaction.user.id] = {
            "code": code,
            "expires": datetime.now(tz=timezone.utc) + timedelta(minutes=10),
            "user": interaction.user,
            "channel": interaction.channel,
        }
        
        await interaction.followup.send(
            f"Open Legion TD 2 and send this message in the global chat within the next 10 minutes:\n```{code}```",
            ephemeral=True
        )
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id != self.global_chat_id:
            return
        if not message.webhook_id or not message.author.display_name.endswith("[Game Chat]"):
            return
        now = datetime.now(tz=timezone.utc)
        expired_users = []
        for user_id, auth_data in list(self.auth_requests.items()):
            if now > auth_data["expires"]:
                try:
                    await auth_data["user"].send(
                        f"<@{user_id}> authentication timed out. Please try again using /rank."
                    )
                except Exception:
                    channel_ids = get_channels(self.guild_id)
                    guild = self.bot.get_guild(self.guild_id)
                    botmsgs = guild.get_channel(channel_ids["public_warn"])
                    await botmsgs.send(f"{auth_data["user"].mention} authentication timed out. Please try again using /rank.")
                expired_users.append(user_id)
            elif auth_data["code"] in message.content:
                await asyncio.sleep(0.5)
                await message.delete()
                success = await self.process_authentication(message.author.display_name.replace(" [Game Chat]", ""), user_id, auth_data["code"])
                if not success:
                    try:
                        await auth_data["user"].send(
                            f"<@{user_id}> authentication failed. Please try again later."
                        )
                    except Exception:
                        channel_ids = get_channels(self.guild_id)
                        guild = self.bot.get_guild(self.guild_id)
                        botmsgs = guild.get_channel(channel_ids["public_warn"])
                        await botmsgs.send(f"{auth_data["user"].mention} authentication failed. Please try again using /rank.")
                break
        for user_id in expired_users:
            del self.auth_requests[user_id]
    
    async def get_player_api_stats(self, playername, by_id = False):
        if by_id:
            player_id = playername
        else:
            request_type = 'players/byName/'
            url = 'https://apiv2.legiontd2.com/' + request_type + playername
            async with self.session.get(url) as response:
                if response.status != 200:
                    return 0, 0
                playerprofile = json.loads(await response.text())
            player_id = playerprofile["_id"]
        request_type = 'players/stats/'
        url = 'https://apiv2.legiontd2.com/' + request_type + player_id
        async with self.session.get(url) as response:
            if response.status != 200:
                return 0, 0
            return json.loads(await response.text()), player_id
    
    async def process_authentication(self, playername, discord_user_id, code):
        del self.auth_requests[discord_user_id]
        stats, player_id = await self.get_player_api_stats(playername)
        if not stats:
            return False
        try:
            rank = get_rank_name(stats["overallElo"])
        except KeyError:
            return False
        discord_user = await self.bot.fetch_user(discord_user_id)
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(discord_user_id)
        rank_role_id = self.rank_roles.get(rank)
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO users (discord_id, player_id, rank)
                    VALUES (?, ?, ?)
                """, (discord_user_id, player_id, rank))
                await db.commit()
            
            if rank_role_id:
                rank_role = guild.get_role(rank_role_id)
                await member.add_roles(rank_role)
                try:
                    await discord_user.send(f"Authentication successful! You have been assigned the rank: {rank}{rank_emotes.get(rank)}")
                except Exception:
                    channel_ids = get_channels(self.guild_id)
                    guild = self.bot.get_guild(self.guild_id)
                    botmsgs = guild.get_channel(channel_ids["public_warn"])
                    await botmsgs.send(f"{discord_user.mention} Authentication successful! You have been assigned the rank: {rank}{rank_emotes.get(rank)}")
        except aiosqlite.IntegrityError:
            try:
                await discord_user.send("This game account is already linked to another Discord account.")
            except Exception:
                channel_ids = get_channels(self.guild_id)
                guild = self.bot.get_guild(self.guild_id)
                botmsgs = guild.get_channel(channel_ids["public_warn"])
                await botmsgs.send(f"{discord_user.mention} This game account is already linked to another Discord account.")
        return True
        
    
    @app_commands.command(name="update-rank", description="Update your rank badge.")
    async def update_rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT player_id FROM users WHERE discord_id = ?", (str(interaction.user.id),)) as cursor:
                result = await cursor.fetchone()
        
        if not result:
            await interaction.followup.send("You need to authenticate first using /rank.", ephemeral=True)
            return
        
        player_id = result[0]
        stats, player_id = await self.get_player_api_stats(player_id, by_id=True)
        try:
            rank = get_rank_name(stats["overallElo"])
        except KeyError:
            await interaction.followup.send(f"Something went wrong :/", ephemeral=True)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET rank = ? WHERE discord_id = ?", (rank, str(interaction.user.id)))
            await db.commit()
        
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(interaction.user.id)
        
        for role_name, role_id in self.rank_roles.items():
            role = guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
        
        new_rank_role = guild.get_role(self.rank_roles[rank])
        await member.add_roles(new_rank_role)
        await interaction.followup.send(f"Your rank has been updated to: {rank}{rank_emotes.get(rank)}", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(GameAuthCog(bot))
