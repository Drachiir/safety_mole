import asyncio
import datetime
import json
import pathlib
import traceback
import typing
from pathlib import Path
import discord
from discord import app_commands
from datetime import datetime, timedelta, timezone
from discord.ext import commands

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()
    
def get_channels(guild_id):
    try:
        with open(f"Files/Config/{guild_id}.json", "r") as f:
            return json.load(f)
    except Exception:
        return None
    
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
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** banned **{user.mention}**"
                                                          f"\n**User id:** {user.id}\n**Reason:** {reason}")
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(user, reason=reason, delete_message_days=delete_message_days)
        except Exception:
            await interaction.followup.send(f"Cannot ban {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been banned for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been banned.", ephemeral=True)
    
    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(userid="Enter userid (Integer) to be unbanned", reason="Reason for the unban")
    async def unban(self, interaction: discord.Interaction, userid: str, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            user = await self.bot.fetch_user(int(userid))
        except discord.NotFound:
            await interaction.followup.send(f"User not found or invalid integer.", ephemeral=True)
            return
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** unbanned **{user.mention}**"
                                                          f"\n**User id:** {user.id}\n**Reason:** {reason}")
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.unban(user, reason=reason)
        except Exception:
            await interaction.followup.send(f"Cannot ban {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0x2BDE19, title=f"You have been unbanned.")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been unbanned, but has DMs disabled so i couldn't inform them about being unbanned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been unbanned.", ephemeral=True)
    
    @app_commands.command(name="soft-ban", description="Kicks a user and deletes their messages")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be soft-banned", reason="Reason for the soft-ban", delete_message_days="Delete messages from this user within X days. Default 7")
    async def softban(self, interaction: discord.Interaction, user: discord.User, reason: str, delete_message_days: typing.Literal['1day', '3days', '5days', '7days']="7days"):
        await interaction.response.defer(thinking=True, ephemeral=True)
        delete_message_days = int(delete_message_days.replace("days", ""))
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** soft-banned **{user.mention}**"
                                                          f"\n**User id:** {user.id}\n**Reason:** {reason}")
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(user, reason=reason, delete_message_days=delete_message_days)
            await asyncio.sleep(1)
            await interaction.guild.unban(user)
        except Exception:
            await interaction.followup.send(f"Cannot soft-ban {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been soft-banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been soft-banned.", ephemeral=True)
    
    @app_commands.command(name="kick", description="Kicks a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be kicked", reason="Reason for the kick")
    async def kick(self, interaction: discord.Interaction, user: discord.User, reason: str, delete_message_days: int):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** kicked **{user.mention}**"
                                                          f"\n**User id:** {user.id}\n**Reason:** {reason}")
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.kick(user, reason=reason)
        except Exception:
            await interaction.followup.send(f"Cannot kick {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been kicked, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been kicked.", ephemeral=True)
    
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be warned", reason="The user will see this as: You have been warned for {reason}.")
    async def warn(self, interaction: discord.Interaction, user: discord.User, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** privately warned **{user.mention}**"
                                                          f"\n**User id:** {user.id}\n**Reason:** {reason}")
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been warned for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await user.send(embed=embed2)
        except Exception:
            #PUBLIC WARN
            embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** publicly warned **{user.mention}**"
                                                              f"\n**User id:** {user.id}\n**Reason:** {reason}")
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            await modlogs.send(embed=embed)
            botmsgs = await self.bot.fetch_channel(channel_ids["public_warn"])
            await botmsgs.send(f"{user.mention} you have been warned for {reason}.")
            await interaction.followup.send(f"{user.mention} has publicly been warned.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"{user.mention} has been privately warned.", ephemeral=True)
    
    @app_commands.command(name="mute", description="Mutes a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be muted", reason="Mute reason")
    async def mute(self, interaction: discord.Interaction, user: discord.Member, reason: str, duration: typing.Literal['60mins', '1days', '3days', '7days', '14days']):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            if duration.endswith("mins"):
                duration_dt = timedelta(minutes=int(duration.replace("mins", "")))
            else:
                duration_dt = timedelta(days=int(duration.replace("days", "")))
            
            embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** muted **{user.mention}**"
                                                              f"\n**Duration:** {duration}"
                                                              f"\n**User id:** {user.id}\n**Reason:** {reason}")
            try:
                await user.timeout(duration_dt, reason=reason)
            except Exception:
                await interaction.followup.send(f"Cannot mute {user.mention}.", ephemeral=True)
                return
            deleted_messages_log = []
            if reason.lower() in ["spam", "scam"]:
                one_hour_ago = datetime.now(tz=timezone.utc) - timedelta(hours=1)
                
                for channel in interaction.guild.text_channels:
                    if channel.category:
                        excluded_keywords = [
                            "staff", "moderation", "info", "new players",
                            "community helper", "tournament casters",
                            "debug", "other", "archived", "voice"
                        ]
                        if any(keyword in channel.category.name.lower() for keyword in excluded_keywords):
                            continue
                    try:
                        async for message in channel.history(limit=100, after=one_hour_ago):
                            if message.author == user:
                                deleted_messages_log.append(f"[{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {message.content}")
                                await message.delete()
                    except discord.Forbidden:
                        continue
                    except discord.HTTPException:
                        pass
            channel_ids = get_channels(interaction.guild.id)
            if not channel_ids:
                await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
                return
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            await modlogs.send(embed=embed)
            if deleted_messages_log:
                deleted_messages_text = "\n".join(deleted_messages_log)
                messages_embed = discord.Embed(
                    color=0xFF4500,
                    title=f"Deleted Messages from {user.display_name}\nLast 1 hour, reason: spam",
                    description=deleted_messages_text[:4096]
                )
                await modlogs.send(embed=messages_embed)
            embed2 = discord.Embed(color=0xDE1919, title=f"You have been muted for {reason}\nDuration: {duration}")
            embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
            try:
                await user.send(embed=embed2)
            except Exception:
                pass
            await interaction.followup.send(f"{user.mention} has been muted for {duration}.", ephemeral=True)
        except Exception:
            traceback.print_exc()
    
    @app_commands.command(name="unmute", description="Unmutes a user")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(user="Select a user to be unmuted", reason="Unmute reason")
    async def unmute(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** unmuted **{user.mention}**"
                                                          f"\n**User id:** {user.id}\n**Reason:** {reason}")
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await user.timeout(timedelta(seconds=0), reason=reason)
        except Exception:
            traceback.print_exc()
            await interaction.followup.send(f"Cannot unmute {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0x2BDE19, title=f"You have been unmuted.\n")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            pass
        await interaction.followup.send(f"{user.mention} has been unmuted.", ephemeral=True)
    
    @app_commands.command(name="proxy", description="Uses Safety Mole to write a message in a given channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(channel="Select a channel for your message", message="Write message")
    async def proxy(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):
        await interaction.response.defer(thinking=True, ephemeral=True)
        if not channel:
            channel = interaction.channel
        channel_ids = get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        message_data = await channel.send(message)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** sent a proxy message to {channel.mention}"
                                                          f"\n**Message link:**{message_data.jump_url}"
                                                          f"\n**Message content:**\n{message}")
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"Message has been sent.", ephemeral=True)
    
    @app_commands.command(name="setup", description="Select channels for public-warn and mod-logs")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(public_warn_channel="Select a channel for Public warnings", mod_logs="Select a channel for Mod-logs")
    async def setup(self, interaction: discord.Interaction, public_warn_channel: discord.TextChannel, mod_logs: discord.TextChannel):
        await interaction.response.defer(thinking=True, ephemeral=True)
        channels = {
            "public_warn": public_warn_channel.id,
            "mod_logs": mod_logs.id
        }
        with open(f"Files/Config/{interaction.guild.id}.json", "w") as f:
            json.dump(channels, f)
            f.close()
        await interaction.followup.send(f"Setup done.", ephemeral=True)
    
    @app_commands.command(name="chat-search", description="Search a chat for specific messages")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(channel="Select a channel for Public warnings", keyword="The keyword to search for.", limit="Search limit, recommended: 10000. Bigger number = longer query")
    async def chat_search(self, interaction: discord.Interaction, channel: discord.TextChannel, keyword: str, limit: int):
        await interaction.response.defer(thinking=True)
        msg: discord.Message
        msg_list=""
        count = 0
        async for msg in channel.history(limit=limit):
            if (keyword.casefold() in msg.author.name.casefold()) or (keyword.casefold() in msg.content.casefold()):
                msg_list += (f"Author: {msg.author}, Date {msg.created_at.date()}, Channel: {msg.channel.name}\n"
                             f"Message: {msg.content}\n"
                             f"{msg.jump_url}\n\n")
                count += 1
        with open("results.txt", "w") as file:
            file.write(msg_list)
        await interaction.followup.send(f"Search done. {count} results found with keyword: '{keyword}'.", file=discord.File("results.txt", filename="results.txt"))
    
async def setup(bot:commands.Bot):
    await bot.add_cog(Moderation(bot))