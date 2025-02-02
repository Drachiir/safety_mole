import asyncio
import json
import datetime
import traceback
import typing
from datetime import timedelta
from datetime import datetime, timedelta, timezone
import aiohttp
import discord
from discord import app_commands, ui, Interaction
from discord._types import ClientT
from discord.ext import commands
import cogs.moderation as modcog
from util import create_mod_log_embed

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class ContextInput(ui.Modal):
    answer = ui.TextInput(label='Enter Text', style=discord.TextStyle.long)
    
    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        await interaction.response.defer()


class ContextMuteInput(ui.Modal):
    duration = ui.TextInput(label='Duration', style=discord.TextStyle.short, max_length=3, placeholder="m = minutes, h = hours, d= days")
    reason = ui.TextInput(label='Reason', style=discord.TextStyle.short)
    
    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        await interaction.response.defer()


class ContextMenu(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.session = aiohttp.ClientSession(headers={'x-api-key': secret_file.get('apikey')})
        self.ctx_delete = app_commands.ContextMenu(name='Delete Message',callback=self.delete)
        self.ctx_ban = app_commands.ContextMenu(name='Ban User',callback=self.contextban)
        self.ctx_soft = app_commands.ContextMenu(name='Soft Ban User',callback=self.contextsoftban)
        self.ctx_kick = app_commands.ContextMenu(name='Kick User',callback=self.contextkick)
        self.ctx_warn = app_commands.ContextMenu(name='Warn User',callback=self.contextwarn)
        self.ctx_proxy = app_commands.ContextMenu(name='Proxy Reply',callback=self.contextproxy)
        self.ctx_mute = app_commands.ContextMenu(name='Mute User',callback=self.contextmute)
        self.ctx_mass_delete = app_commands.ContextMenu(name='Mass delete', callback=self.context_mass_delete)
        #Add commands to command tree
        self.bot.tree.add_command(self.ctx_delete)
        self.bot.tree.add_command(self.ctx_ban)
        self.bot.tree.add_command(self.ctx_soft)
        self.bot.tree.add_command(self.ctx_kick)
        self.bot.tree.add_command(self.ctx_warn)
        self.bot.tree.add_command(self.ctx_proxy)
        self.bot.tree.add_command(self.ctx_mute)
        self.bot.tree.add_command(self.ctx_mass_delete)
        
    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_delete.name, type=self.ctx_delete.type)
        self.bot.tree.remove_command(self.ctx_ban.name, type=self.ctx_ban.type)
        self.bot.tree.remove_command(self.ctx_soft.name, type=self.ctx_soft.type)
        self.bot.tree.remove_command(self.ctx_kick.name, type=self.ctx_kick.type)
        self.bot.tree.remove_command(self.ctx_warn.name, type=self.ctx_warn.type)
        self.bot.tree.remove_command(self.ctx_proxy.name, type=self.ctx_proxy.type)
        self.bot.tree.remove_command(self.ctx_mute.name, type=self.ctx_mute.type)
        self.bot.tree.remove_command(self.ctx_mass_delete.name, type=self.ctx_mass_delete.type)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def delete(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.defer(thinking=True, ephemeral=True)
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await interaction.followup.send("Message deleted", ephemeral=True)
        files = []
        if message.attachments:
            for i, att in enumerate(message.attachments):
                files.append(await att.to_file(filename=f"temp{i}.png"))
        await message.delete()
        if message.author.display_name.endswith("[Game Chat]"):
            embed_name = message.author.display_name
            #pull playfab id from api
            request_type = 'players/byName/'
            playername = message.author.display_name.replace(" [Game Chat]", "")
            url = 'https://apiv2.legiontd2.com/' + request_type + playername
            async with self.session.get(url) as response:
                if response.status != 200:
                    user_id = ""
                else:
                    player_profile = json.loads(await response.text())
                    user_id = f"\n**Kraken:** https://kraken.legiontd2.com/playerid/{player_profile["_id"]}"
        else:
            embed_name = message.author.display_name
            user_id = f"\n**User id:** {message.author.id}"
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** deleted a message from **{embed_name}**"
                                                          f"{user_id}"
                                                          f"\n**Channel:** {message.channel.mention}"
                                                          f"\n**Message Date:** {message.created_at.strftime("%d/%m/%Y, %H:%M:%S")}"
                                                          f"\n**Message Content:**\n{message.content}")
        if message.attachments:
            if len(files) == 1:
                embed.set_image(url="attachment://temp0.png")
                await modlogs.send(embed=embed, file=files[0])
            else:
                await modlogs.send(embed=embed)
                await modlogs.send(files=files)
        else:
            await modlogs.send(embed=embed)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def contextban(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Ban")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = create_mod_log_embed(interaction.user, "banned", user, reason)
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(user, reason=reason)
        except Exception:
            await interaction.followup.send(f"Cannot ban {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been banned {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been banned.", ephemeral=True)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def contextsoftban(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Soft-Ban")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = create_mod_log_embed(interaction.user, "soft-banned", user, reason)
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(user)
            await asyncio.sleep(1)
            await interaction.guild.unban(user)
        except Exception:
            await interaction.followup.send(f"Cannot soft-ban {user.mention}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been soft-banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been soft-banned.", ephemeral=True)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def contextkick(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Kick")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = create_mod_log_embed(interaction.user, "kicked", user, reason)
        channel_ids = modcog.get_channels(interaction.guild.id)
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
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.mention} has been kicked, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.mention} has been kicked.", ephemeral=True)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def contextwarn(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Warning")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = create_mod_log_embed(interaction.user, "privately warned", user, reason)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been warned: {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await user.send(embed=embed2)
        except Exception:
            #PUBLIC WARN
            embed = create_mod_log_embed(interaction.user, "publicly warned", user, reason)
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            await modlogs.send(embed=embed)
            botmsgs = await self.bot.fetch_channel(channel_ids["public_warn"])
            await botmsgs.send(f"{user.mention} You have been warned: {reason}")
            await interaction.followup.send(f"{user.mention} has publicly been warned.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"{user.mention} has been privately warned.", ephemeral=True)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def contextproxy(self, interaction: discord.Interaction, message: discord.Message):
        context_modal = ContextInput(title="Enter Message for Proxy Reply")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        proxy_reply = context_modal.answer.value
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        message_data = await message.reply(proxy_reply)
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** sent a proxy message to {message.channel.mention}"
                                                          f"\n**Message link:**{message_data.jump_url}"
                                                          f"\n**Message content:**\n{proxy_reply}")
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"Message has been sent.", ephemeral=True)
    
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def contextmute(self, interaction: discord.Interaction, user: discord.Member):
        context_modal = ContextMuteInput(title="Enter duration e.g 60m")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        duration = context_modal.duration.value
        reason = context_modal.reason.value
        if duration[-1] not in ["m","h","d"]:
            await interaction.followup.send(f"Invalid duration input, needs to be a number followed by either m = minutes, h = hours or d= days.\n"
                                            f"e.g. 60m", ephemeral=True)
            return
        try:
            if duration.endswith("m"):
                duration_dt = timedelta(minutes=int(duration.replace("m", "")))
            elif duration.endswith("h"):
                duration_dt = timedelta(hours=int(duration.replace("h", "")))
            else:
                duration_dt = timedelta(days=int(duration.replace("d", "")))
            embed = create_mod_log_embed(interaction.user, "muted", user, reason, duration=duration)
        except Exception:
            traceback.print_exc()
            await interaction.followup.send(f"Invalid duration input, needs to be a number followed by either m = minutes, h = hours or d= days.\n"
                                            f"e.g. 1d", ephemeral=True)
            return
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
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

    class DeleteMessagesModal(discord.ui.Modal):
        def __init__(self, interaction: discord.Interaction, target_message: discord.Message, bot: commands.Bot, session):
            self.interaction = interaction
            self.target_message = target_message
            self.bot = bot
            self.session = session
            super().__init__(title="Mass Delete Messages")

            self.add_item(discord.ui.TextInput(
                label="Number of messages to delete",
                placeholder="Enter a number",
                required=True,
                style=discord.TextStyle.short
            ))

        async def on_submit(self, interaction: discord.Interaction):
            try:
                num_messages = int(self.children[0].value)
                if num_messages <= 0:
                    raise ValueError("Number must be greater than 0.")
            except ValueError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
                return

            author_name = self.target_message.author.name
            is_webhook = bool(self.target_message.webhook_id)

            await interaction.response.send_message(
                f"Starting mass delete for {num_messages} messages from {'webhook' if is_webhook else 'user'} '{author_name}'.",
                ephemeral=True
            )
            deleted_messages = []
            async for msg in self.target_message.channel.history(limit=5000):
                if len(deleted_messages) >= num_messages:
                    break
                if msg.webhook_id == self.target_message.webhook_id and msg.author.name == author_name:
                    deleted_messages.append(msg)
                    await msg.delete()
                    await asyncio.sleep(0.5)
                elif not msg.webhook_id and msg.author.id == self.target_message.author.id:
                    deleted_messages.append(msg)
                    await msg.delete()
                    await asyncio.sleep(0.5)

            deleted_count = len(deleted_messages)
            channel_ids = modcog.get_channels(interaction.guild.id)
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            if modlogs:
                if self.target_message.author.display_name.endswith("[Game Chat]"):
                    request_type = 'players/byName/'
                    playername = self.target_message.author.display_name.replace(" [Game Chat]", "")
                    url = 'https://apiv2.legiontd2.com/' + request_type + playername
                    async with self.session.get(url) as response:
                        if response.status != 200:
                            user_id = ""
                        else:
                            player_profile = json.loads(await response.text())
                            user_id = f"\n**Kraken:** https://kraken.legiontd2.com/playerid/{player_profile["_id"]}"
                else:
                    user_id = f"\n**User id:** {self.target_message.author.id}"
                embed = discord.Embed(
                    description=f"{interaction.user.mention} deleted {deleted_count} messages from **{author_name}**"
                                f"{user_id}\n"
                                f"**Channel:** {self.target_message.channel.mention}\n",
                    color=discord.Color.red()
                )
                embed.add_field(name="Messages Deleted:", value="\n".join(f"- {msg.content}" for msg in deleted_messages) or "No message content available.", inline=False)
                await modlogs.send(embed=embed)

    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    async def context_mass_delete(self, interaction: discord.Interaction, message: discord.Message):
        """
        Context menu command to delete messages from a webhook.
        """
        await interaction.response.send_modal(self.DeleteMessagesModal(interaction, message, bot=self.bot, session=self.session))

async def setup(bot:commands.Bot):
    await bot.add_cog(ContextMenu(bot))