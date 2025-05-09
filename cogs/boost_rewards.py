import json
import pathlib
import aiofiles
import discord
import random
import string
import aiosqlite
from datetime import datetime, timedelta, timezone
from discord.ext import commands, tasks
from aiohttp import web
from discord import app_commands
from types import SimpleNamespace
from datetime import datetime, timedelta

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
VERIFIED_ROLE = config["VERIFIED_ROLE"]
DB_PATH = str(pathlib.Path(__file__).parent.parent.resolve()) + config["DB_PATH"]
DEBUG = config["DEBUG"]

class BoostRewardsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = DB_PATH
        self.check_monthly_boosts.start()

    def cog_unload(self):
        self.check_monthly_boosts.cancel()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.display_name.casefold() != "dani":
            return
        if not before.premium_since and after.premium_since:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            boost_start = after.premium_since.isoformat()
            current_month = datetime.utcnow().strftime("%Y-%m")

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO boost_codes (discord_id, code, boost_start, last_reward_month)
                    VALUES (?, ?, ?, ?)
                """, (str(after.id), code, boost_start, current_month))
                await db.commit()

            try:
                await after.send(
                    f"Thanks for boosting our server ❤️\n"
                    f"Enter this in the LegionTD2 Global Chat to claim a reward! `/redeem {code}`\n"
                    f"-# The code expires in a month."
                )
            except discord.HTTPException:
                channel_ids = get_channels(GUILD_ID)
                botmsgs = await self.bot.fetch_channel(channel_ids["public_warn"])
                if botmsgs:
                    await botmsgs.send(
                        f"{after.mention}, We tried to send you your boost reward code, but DMs are disabled. Use `/boost-reward` to retrieve it!"
                    )

    @app_commands.command(name="boost-reward", description="Get your reward for boosting the LTD2 discord server.")
    async def getcode(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT code FROM boost_codes WHERE discord_id = ?", (str(interaction.user.id),)) as cursor:
                row = await cursor.fetchone()

        if row and row[0]:
            await interaction.followup.send(f"Your active boost reward code is: `/redeem {row[0]}`", ephemeral=True)
        else:
            await interaction.followup.send("No active code found for you. You will get a code every month you boost the LTD2 discord.", ephemeral=True)

    @tasks.loop(hours=24)
    async def check_monthly_boosts(self):
        guild = await self.bot.fetch_guild(GUILD_ID)
        if not guild:
            return

        print("Running daily discord boost check...")
        now = datetime.now(timezone.utc)

        async with aiosqlite.connect(self.db_path) as db:
            # async with db.execute("SELECT discord_id FROM boost_codes") as cursor:
            #     rows = await cursor.fetchall()
            #
            # for row in rows:
            #     discord_id = row[0]
            #     member = await guild.fetch_member(int(discord_id))
            #     print(member)
            #     if not member:
            #         continue  # skip if user not in guild
            for member in guild.premium_subscribers:
                if member.display_name.casefold() != "dani":
                    continue
                discord_id = str(member.id)

                async with db.execute("""
                    SELECT boost_start, last_reward_month FROM boost_codes WHERE discord_id = ?
                """, (discord_id,)) as cursor:
                    row = await cursor.fetchone()

                if not row:
                    # New booster who hasn't received any rewards yet
                    boost_start = member.premium_since.isoformat() if member.premium_since else now.isoformat()
                    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
                    new_reward_month = now.strftime("%Y-%m")

                    await db.execute("""
                        INSERT INTO boost_codes (discord_id, code, boost_start, last_reward_month)
                        VALUES (?, ?, ?, ?)
                    """, (discord_id, new_code, boost_start, new_reward_month))
                    await db.commit()

                    try:
                        await member.send(
                            f"Thanks for boosting our server ❤️\n"
                            f"Enter this in the LegionTD2 Global Chat to claim a reward! `/redeem {new_code}`\n"
                            f"-# The code expires in a month."
                        )
                        print(f"{member.display_name} boosted the ltd2 server!")
                    except discord.HTTPException:
                        try:
                            channel_ids = await get_channels(GUILD_ID)
                            if channel_ids and "public_warn" in channel_ids:
                                channel = await self.bot.fetch_channel(channel_ids["public_warn"])
                                await channel.send(
                                    f"{member.mention}, we tried to send your monthly boost reward, but DMs are disabled. "
                                    f"Use `/boost-reward` to retrieve it!"
                                )
                        except Exception:
                            pass
                    continue  # Skip further processing for this member

                # Existing booster: check if they’re due for a monthly reward
                boost_start_str, last_reward_month = row
                boost_start = datetime.fromisoformat(boost_start_str)
                give_reward = False

                if not last_reward_month:
                    # First monthly reward since tracking began
                    give_reward = True
                else:
                    # Get expected monthly reward date for this month
                    reward_day = min(boost_start.day, 28)  # cap to 28 to avoid invalid dates in Feb
                    reward_date_this_month = datetime(now.year, now.month, reward_day, tzinfo=timezone.utc)

                    last_reward_dt = datetime.strptime(last_reward_month, "%Y-%m")
                    months_since_last = (now.year - last_reward_dt.year) * 12 + (now.month - last_reward_dt.month)

                    # Only reward if we're on or after their reward anniversary day, and haven't already rewarded this month
                    if now >= reward_date_this_month and months_since_last >= 1:
                        give_reward = True

                if give_reward:
                    new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
                    new_reward_month = now.strftime("%Y-%m")

                    await db.execute("""
                        UPDATE boost_codes
                        SET code = ?, last_reward_month = ?
                        WHERE discord_id = ?
                    """, (new_code, new_reward_month, discord_id))
                    await db.commit()

                    try:
                        await member.send(
                            f"Thanks for continuing to boost our server this month! 🎉\n"
                            f"Enter this in the LegionTD2 Global Chat to claim a reward! `/redeem {new_code}`\n"
                            f"-# The code expires in a month."
                        )
                    except discord.HTTPException:
                        try:
                            channel_ids = await get_channels(GUILD_ID)
                            if channel_ids and "public_warn" in channel_ids:
                                channel = await self.bot.fetch_channel(channel_ids["public_warn"])
                                await channel.send(
                                    f"{member.mention}, we tried to send your monthly boost reward, but DMs are disabled. "
                                    f"Use `/boost-reward` to retrieve it!"
                                )
                        except Exception:
                            pass

    @app_commands.command(name="boosting_since", description="Check when a user started boosting the server")
    @app_commands.describe(user="The user to check")
    @app_commands.default_permissions(ban_members=True)
    async def boosting_since(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(thinking=True, ephemeral=True)
        if not user.premium_since:
            await interaction.followup.send(f"{user.mention} is not currently boosting the server.", ephemeral=True)
            return

        boosting_since = user.premium_since.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = now - boosting_since

        await interaction.followup.send(
            f"{user.mention} has been boosting since **{boosting_since.strftime('%Y-%m-%d %H:%M:%S')} UTC** "
            f"(*{delta.days} days ago*)", ephemeral=True)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testboost(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        now = datetime.utcnow()

        # Create fake before and after objects
        before = SimpleNamespace(
            id=member.id,
            premium_since=None,
            mention=member.mention,
            send=lambda msg: ctx.send(f"(Simulated DM to {member.display_name}): {msg}")
        )

        after = SimpleNamespace(
            id=member.id,
            premium_since=now - timedelta(days=1),
            mention=member.mention,
            send=lambda msg: ctx.send(f"(Simulated DM to {member.display_name}): {msg}")
        )

        await self.on_member_update(before, after)
        await ctx.send("Test boost event triggered.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testboostmonth(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        now = datetime.utcnow()
        fake_boost_start = (now - timedelta(days=32)).replace(hour=0, minute=0, second=0)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO boost_codes (discord_id, code, boost_start, last_reward_month)
                VALUES (?, NULL, ?, ?)
            """, (str(member.id), fake_boost_start.isoformat(), (now - timedelta(days=32)).strftime("%Y-%m")))
            await db.commit()

        await self.check_monthly_boosts()
        await ctx.send(f"Simulated monthly check for {member.display_name}.")

    @check_monthly_boosts.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(BoostRewardsCog(bot))
