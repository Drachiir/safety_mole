import discord
from discord.ext import commands
import aiosqlite
import json

class RoleReaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_message_id = None

    async def cog_load(self):
        async with aiosqlite.connect("roles.db") as db:
            await db.execute(
                "CREATE TABLE IF NOT EXISTS role_reactions (message_id INTEGER, emoji TEXT, role_id INTEGER)"
            )
            await db.commit()

            await db.execute(
                "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
            )
            await db.commit()

            async with db.execute("SELECT value FROM settings WHERE key = 'role_message_id'") as cursor:
                row = await cursor.fetchone()
                if row:
                    self.role_message_id = int(row[0])
                    print(f"Loaded role message ID: {self.role_message_id}")

    @commands.command(name="setup_roles")
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx):
        description = (
            "🏆 `- Tournaments`\n\n"
            "🧑‍💻 `- Community Development`\n\n"
            "🔍 `- Game Starts/Results`\n\n"
            "📚 `- Archive`"
        )
        embed = discord.Embed(title="React to get access to hidden channel categories", description=description, color=discord.Color.blue())
        message = await ctx.send(embed=embed)

        reactions = ["🏆", "🧑‍💻", "🔍", "📚"]
        for emoji in reactions:
            await message.add_reaction(emoji)

        self.role_message_id = message.id

        with open("Files/json/reaction_roles.json", "r") as config_file:
            config = json.load(config_file)

        role_mapping = {
            "🏆": config["TOURNAMENTS"],
            "🧑‍💻": config["COMMUNITY_DEV"],
            "🔍": config["GAME_STARTS_RESULTS"],
            "📚": config["ARCHIVE"],
        }

        async with aiosqlite.connect("roles.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("role_message_id", str(message.id)),
            )
            for emoji, role_id in role_mapping.items():
                await db.execute(
                    "INSERT INTO role_reactions (message_id, emoji, role_id) VALUES (?, ?, ?)",
                    (message.id, emoji, role_id),
                )
            await db.commit()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id != self.role_message_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        async with aiosqlite.connect("roles.db") as db:
            async with db.execute(
                "SELECT role_id FROM role_reactions WHERE message_id = ? AND emoji = ?",
                (payload.message_id, str(payload.emoji)),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    role = guild.get_role(row[0])
                    if role:
                        member = guild.get_member(payload.user_id)
                        if member:
                            await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id != self.role_message_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        async with aiosqlite.connect("roles.db") as db:
            async with db.execute(
                "SELECT role_id FROM role_reactions WHERE message_id = ? AND emoji = ?",
                (payload.message_id, str(payload.emoji)),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    role = guild.get_role(row[0])
                    if role:
                        member = guild.get_member(payload.user_id)
                        if member:
                            await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(RoleReaction(bot))
