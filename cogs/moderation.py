import datetime
import json
import typing

import discord
from discord import app_commands
from discord.ext import commands

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="ban", description="Permanently ban a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be banned", reason="Reason for the ban", delete_message_days="Delete messages from this user within X days. Default 7")
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str, delete_message_days: typing.Literal['1day', '3days', '5days', '7days']="7days"):
        await interaction.response.defer(thinking=True, ephemeral=True)
        delete_message_days = int(delete_message_days.replace("days", ""))
        await interaction.guild.ban(user, reason=reason, delete_message_days=delete_message_days)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** banned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been banned for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has been banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.display_name} has been banned.", ephemeral=True)
    
    @app_commands.command(name="soft-ban", description="Kicks a user and deletes their messages")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be soft-banned", reason="Reason for the soft-ban", delete_message_days="Delete messages from this user within X days. Default 7")
    async def softban(self, interaction: discord.Interaction, user: discord.User, reason: str, delete_message_days: typing.Literal['1day', '3days', '5days', '7days']="7days"):
        await interaction.response.defer(thinking=True, ephemeral=True)
        delete_message_days = int(delete_message_days.replace("days", ""))
        await interaction.guild.ban(user, reason=reason, delete_message_days=delete_message_days)
        await interaction.guild.unban(user)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** soft-banned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has been soft-banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.display_name} has been soft-banned.", ephemeral=True)
    
    @app_commands.command(name="kick", description="Kicks a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be kicked", reason="Reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.User, reason: str, delete_message_days: int):
        await interaction.response.defer(thinking=True, ephemeral=True)
        await interaction.guild.kick(user, reason=reason)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** kicked **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has been kicked, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.display_name} has been kicked.", ephemeral=True)
    
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be warned", reason="Warning reason")
    async def warn(self, interaction: discord.Interaction, user: discord.User, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** privately warned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been warned for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has DMs disabled, use /public-warn instead.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"{user.display_name} has been warned.", ephemeral=True)
    
    @app_commands.command(name="public-warn", description="Publicly warn a user in #Bot Messages")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be warned", reason="Warning reason")
    async def publicwarn(self, interaction: discord.Interaction, user: discord.User, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** publicly warned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        botmsgs = await self.bot.fetch_channel(secret_file["botmsgid"])
        await botmsgs.send(f"{user.mention} you have been warned for {reason}.")
        await interaction.followup.send(f"{user.display_name} has been warned.", ephemeral=True)
    
    @app_commands.command(name="mute", description="mutes warn a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be muted", reason="Mute reason")
    async def mute(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: typing.Literal['60mins', '1days', '3days', '7days', '14days']):
        await interaction.response.defer(thinking=True, ephemeral=True)
        if duration.endswith("mins"):
            duration_dt = datetime.timedelta(minutes=int(duration.replace("mins", "")))
        else:
            duration_dt = datetime.timedelta(days=int(duration.replace("days", "")))
        await user.timeout(duration_dt, reason=reason)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** muted **{user.display_name}**"
                                                          f"\n**Duration:** {duration}"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been muted for {reason}\nDuration: {duration}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            pass
        await interaction.followup.send(f"{user.display_name} has been timed out.", ephemeral=True)
    
    @app_commands.command(name="proxy", description="Uses Safety Mole to write a message in a given channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(channel="Select a channel for your message", message="Write message")
    async def proxy(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        message_data = await channel.send(message)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** sent a proxy message to {channel.mention}"
                                                          f"\n**Message link:**{message_data.jump_url}"
                                                          f"\n**Message content:**\n{message}")
        modlogs = await self.bot.fetch_channel(secret_file["modlogsid"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"Message has been sent.", ephemeral=True)
    
async def setup(bot:commands.Bot):
    await bot.add_cog(Moderation(bot))