import pathlib
import traceback
import discord
import discord_timestamps
from discord import app_commands
from discord.ext import commands, tasks
import aiosqlite
import aiohttp
import random
import string
from datetime import datetime, timedelta, timezone
import asyncio
import json
import aiofiles
from discord_timestamps import TimestampType
import re
from aiohttp import web

with open("Files/json/rank_roles.json", "r") as config_file:
    config = json.load(config_file)

with open("Files/json/Secrets.json", "r") as secret_file:
    secret = json.load(secret_file)

async def get_channels(guild_id):
    try:
        async with aiofiles.open(f"Files/Config/{guild_id}.json", "r") as f:
            content = await f.read()
        return json.loads(content)
    except Exception:
        return None

GUILD_ID = config["GUILD_ID"]
GLOBAL_CHAT_CHANNEL_ID = config["GLOBAL_CHAT_CHANNEL_ID"]
RANK_ROLES = {rank: int(role_id) for rank, role_id in config["RANK_ROLES"].items()}
RANK_ROLES2 = {rank: int(role_id) for rank, role_id in config["RANK_ROLES2"].items()}
DB_PATH = str(pathlib.Path(__file__).parent.parent.resolve()) + config["DB_PATH"]
DEBUG = config["DEBUG"]

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
    "Unranked": "<:Unranked:1299633644746444830>",
    "Bronze": "<:Bronze:1299633629802139709>",
    "Silver": "<:Silver:1299633694662856705>",
    "Gold": "<:Gold:1299633634596098078>",
    "Platinum": "<:Platinum:1299633639788777544>",
    "Diamond": "<:Diamond:1299633630695522327>",
    "Expert": "<:Expert:1299633632650199091>",
    "Master": "<:Master:1299633638534811659>",
    "SeniorMaster": "<:SeniorMaster:1299633641051394109>",
    "Grandmaster": "<:GrandMaster:1299633635431022657>",
    "Legend": "<:Legend:1299633637049761792>"
}

class GameAuthCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
        self.guild_id = GUILD_ID
        self.global_chat_id = GLOBAL_CHAT_CHANNEL_ID
        self.rank_roles = RANK_ROLES
        self.rank_roles2 = RANK_ROLES2
        self.auth_requests = {}
        self.color = 0xDE1919
        self.session = aiohttp.ClientSession(headers={'x-api-key': secret.get('apikey')})
        self.bot.loop.create_task(self.create_db())
        
        self.web_app = web.Application()
        self.web_app.add_routes([web.get('/ltd2', self.verify_endpoint)])
        self.runner = web.AppRunner(self.web_app)
        self.bot.loop.create_task(self.start_server())
    
    async def start_server(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', 42070)
        await site.start()
    
    #/ltd2?code=7HRBK5PVLSIQ&playFabId=123456&rank=6969&playerName=Drachir
    async def verify_endpoint(self, request):
        code = request.query.get("code")
        playfab_id = request.query.get("playFabId")
        rank = request.query.get("rank")
        playername = request.query.get("playerName")
        if not all([code, playfab_id, rank, playername]):
            return web.json_response({"status": "invalid request"}, status=400)
        for user_id, auth_data in list(self.auth_requests.items()):
            if auth_data["code"] == code:
                try:
                    success = await self.process_authentication(playfab_id, user_id, rank, playername)
                    if success:
                        return web.json_response({"status": "valid"})
                    else:
                        return web.json_response({"status": "invalid"}, status=400)
                except Exception:
                    traceback.print_exc()
                    embed = discord.Embed(color=self.color, description=f"**{auth_data["user"].mention}** authentication failed. Please try again later.")
                    embed.set_author(name="Legion TD 2 Rank Roles", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
                    try:
                        await auth_data["user"].send(embed=embed)
                    except Exception:
                        await self.send_warn_to_channel(f"{auth_data["user"].mention} authentication failed. Please try again later.")
                    return web.json_response({"status": "error"}, status=500)
        return web.json_response({"status": "invalid"}, status=400)
        
    async def create_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id TEXT PRIMARY KEY,
                    player_id TEXT UNIQUE,
                    discord_name TEXT,
                    ingame_name TEXT,
                    rank TEXT
                )
            """)
            await db.commit()
    
    async def cog_unload(self):
        await self.runner.cleanup()
        await self.session.close()
    
    async def send_warn_to_channel(self, message):
        channel_ids = await get_channels(self.guild_id)
        guild = self.bot.get_guild(self.guild_id)
        botmsgs = guild.get_channel(channel_ids["public_warn"])
        await botmsgs.send(message)
    
    @app_commands.command(name="rank", description="Start authentication process to get a rank badge.")
    @app_commands.checks.cooldown(1, 20.0, key=lambda i: (i.guild_id, i.user.id))
    async def rank_role(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        code = f"{(''.join(random.choices(string.ascii_uppercase + string.digits, k=12)))}" #(Do not copy/paste this unless you know why)
        self.auth_requests[interaction.user.id] = {
            "code": code,
            "user": interaction.user,
            "channel": interaction.channel,
        }
        embed = discord.Embed(color=self.color, description=f"**{interaction.user.mention}** **Open Legion TD 2** and,\nsend this command in the **Global Chat**:"
                                                          f"\n```/verify {code}```")
        embed.set_author(name="Legion TD 2 Rank Roles", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def get_player_api_stats(self, player_id):
        request_type = 'players/byId/'
        url = 'https://apiv2.legiontd2.com/' + request_type + player_id
        async with self.session.get(url) as response:
            if response.status != 200:
                return 0, 0
            playerprofile = json.loads(await response.text())
        playername = playerprofile["playerName"]
        request_type = 'players/stats/'
        url = 'https://apiv2.legiontd2.com/' + request_type + player_id
        async with self.session.get(url) as response:
            if response.status != 200:
                return 0, 0
            return json.loads(await response.text()), playername
    
    async def process_authentication(self, player_id, discord_user_id, rank, playername):
        del self.auth_requests[discord_user_id]
        rank = get_rank_name(int(rank))
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(discord_user_id)
        rank_role_id = self.rank_roles.get(rank)
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT discord_id FROM users WHERE player_id = ?", (player_id,)) as cursor:
                    result = await cursor.fetchone()
                
                if result and result[0] != str(discord_user_id):
                    embed = discord.Embed(color=self.color, description=f"**{member.mention}** This game account is already linked to another Discord account.")
                    embed.set_author(name="Legion TD 2 Rank Roles", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
                    try:
                        await member.send(embed=embed)
                    except Exception:
                        await self.send_warn_to_channel(f"{member.mention} This game account is already linked to another Discord account.")
                    return False
                await db.execute("""
                    INSERT OR REPLACE INTO users (discord_id, player_id, discord_name, ingame_name, rank)
                    VALUES (?, ?, ?, ?, ?)
                """, (discord_user_id, player_id, member.display_name, playername, rank))
                await db.commit()
            
            if rank_role_id:
                for role_name, role_id in self.rank_roles.items():
                    role = guild.get_role(role_id)
                    if role in member.roles:
                        await member.remove_roles(role)
                rank_role = guild.get_role(rank_role_id)
                await member.add_roles(rank_role)
                embed_message = (f"**{member.mention} Authentication successful!**\n"
                                f"You have been assigned the rank: **{rank}**{rank_emotes.get(rank)}"
                                f"\nYou can update your rank using **/update-rank** if it changes,"
                                f"\nor **/remove-rank** to remove it.")
                embed = discord.Embed(color=self.color,description=embed_message)
                embed.set_author(name="Legion TD 2 Rank Roles", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
                try:
                    await member.send(embed=embed)
                except Exception:
                    await self.send_warn_to_channel(embed_message)
                print(f"{member.display_name} successfully linked with legion account: {playername}")
        except aiosqlite.IntegrityError:
            embed = discord.Embed(color=self.color, description=f"**{member.mention}** This game account is already linked to another Discord account.")
            embed.set_author(name="Legion TD 2 Rank Roles", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
            try:
                await member.send(embed=embed)
            except Exception:
                await self.send_warn_to_channel(f"{member.mention} This game account is already linked to another Discord account.")
        return True
    
    @app_commands.command(name="update-rank", description="Update your rank badge.")
    @app_commands.checks.cooldown(1, 600.0, key=lambda i: (i.guild_id, i.user.id))
    async def update_rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT player_id FROM users WHERE discord_id = ?", (str(interaction.user.id),)) as cursor:
                result = await cursor.fetchone()
        
        if not result:
            await interaction.followup.send("You need to authenticate first using /rank.", ephemeral=True)
            return
        
        player_id = result[0]
        stats, player_id = await self.get_player_api_stats(player_id)
        try:
            rank = get_rank_name(stats["overallElo"])
        except Exception:
            traceback.print_exc()
            await interaction.followup.send(f"Something went wrong, please try again later.", ephemeral=True)
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
        for role_name, role_id in self.rank_roles2.items():
            role = guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
                new_rank_role = guild.get_role(self.rank_roles2[rank])
                await member.add_roles(new_rank_role)
        await interaction.followup.send(f"Your rank has been updated to: {rank}{rank_emotes.get(rank)}", ephemeral=True)
    
    @update_rank.error
    @rank_role.error
    async def on_test_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            now_date = (datetime.now(tz=timezone.utc)+timedelta(seconds=error.retry_after)).timestamp()
            timestamp = discord_timestamps.format_timestamp(now_date, TimestampType.RELATIVE)
            await interaction.response.send_message(f"Command on cooldown, try again {timestamp}", ephemeral=True)
    
    @app_commands.command(name="show-profile", description="Show drachbot profile of a user, if they are verified.")
    async def show_profile(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=True)
        if not user:
            user_id = interaction.user.id
            username = interaction.user.display_name
        else:
            user_id = user.id
            username = user.display_name
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT player_id FROM users WHERE discord_id = ?", (str(user_id),)) as cursor:
                result = await cursor.fetchone()
        
        if not result:
            await interaction.followup.send("This user is not verified.", ephemeral=True)
            return
        
        player_id = result[0]
        await interaction.followup.send(f"{username} @ Drachbot <:Drachia:1300036826702024825>"
                                        f"\nhttps://drachbot.site/profile/{player_id}", ephemeral=True)
    
    @app_commands.command(name="remove-rank", description="Remove your rank badge and unlink your accounts.")
    async def remove_rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(interaction.user.id)
        roles_removed = False
        for role_name, role_id in self.rank_roles.items():
            role = guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
                roles_removed = True
        for role_name, role_id in self.rank_roles2.items():
            role = guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
                roles_removed = True
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("DELETE FROM users WHERE discord_id = ?", (str(interaction.user.id),)) as cursor:
                await db.commit()
                row_deleted = cursor.rowcount > 0
        
        if not roles_removed and not row_deleted:
            response = "You don't have any rank badge or linked account to remove."
        elif not roles_removed and row_deleted:
            response = "Your linked account has been unlinked, but no rank badge was found to remove."
        elif roles_removed and not row_deleted:
            response = "Your rank badge has been removed, but no linked account was found to unlink."
        else:
            response = "Your rank badge has been removed, and your account has been unlinked."
        
        await interaction.followup.send(response, ephemeral=True)
    
    @app_commands.command(name="toggle-rank-role", description="Toggle rank role over other roles such as Community Helper.")
    async def toggle_rank(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = self.bot.get_guild(GUILD_ID)
        member = guild.get_member(interaction.user.id)
        for role_name, role_id in self.rank_roles.items():
            role = guild.get_role(role_id)
            if role in member.roles:
                await member.remove_roles(role)
                new_role = guild.get_role(self.rank_roles2[role_name])
                await member.add_roles(new_role)
                break
        else:
            for role_name, role_id in self.rank_roles2.items():
                role = guild.get_role(role_id)
                if role in member.roles:
                    await member.remove_roles(role)
                    new_role = guild.get_role(self.rank_roles[role_name])
                    await member.add_roles(new_role)
                    break
                    
        response = f"Rank role toggled."
        await interaction.followup.send(response, ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(GameAuthCog(bot))
