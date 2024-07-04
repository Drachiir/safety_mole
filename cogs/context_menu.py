import asyncio
import json
import discord
from discord import app_commands, ui, Interaction
from discord._types import ClientT
from discord.ext import commands
import cogs.moderation as modcog

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class ContextInput(ui.Modal):
    answer = ui.TextInput(label='Reason', style=discord.TextStyle.short)
    
    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        await interaction.response.defer()


class ContextDelete(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_delete = app_commands.ContextMenu(
            name='Delete Message',
            callback=self.delete
        )
        self.ctx_ban = app_commands.ContextMenu(
            name='Ban User',
            callback=self.contextban
        )
        self.ctx_soft = app_commands.ContextMenu(
            name='Soft Ban User',
            callback=self.contextsoftban
        )
        self.ctx_kick = app_commands.ContextMenu(
            name='Kick User',
            callback=self.contextkick
        )
        self.ctx_warn = app_commands.ContextMenu(
            name='Warn User',
            callback=self.contextwarn
        )
        self.ctx_proxy = app_commands.ContextMenu(
            name='Proxy Reply',
            callback=self.contextproxy
        )
        self.bot.tree.add_command(self.ctx_delete)
        self.bot.tree.add_command(self.ctx_ban)
        self.bot.tree.add_command(self.ctx_soft)
        self.bot.tree.add_command(self.ctx_kick)
        self.bot.tree.add_command(self.ctx_warn)
        self.bot.tree.add_command(self.ctx_proxy)
        
    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_delete.name, type=self.ctx_delete.type)
        self.bot.tree.remove_command(self.ctx_ban.name, type=self.ctx_ban.type)
        self.bot.tree.remove_command(self.ctx_soft.name, type=self.ctx_soft.type)
        self.bot.tree.remove_command(self.ctx_kick.name, type=self.ctx_kick.type)
        self.bot.tree.remove_command(self.ctx_warn.name, type=self.ctx_warn.type)
        self.bot.tree.remove_command(self.ctx_proxy.name, type=self.ctx_proxy.type)
    
    @app_commands.default_permissions(ban_members=True)
    async def delete(self, interaction: discord.Interaction, message: discord.Message):
        await message.delete()
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** deleted a message from **{message.author.display_name}**"
                                                          f"\n**User id**: {message.author.id}"
                                                          f"\n**Channel**: {message.channel.name}"
                                                          f"\n**Message content:**\n{message.content}")
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.response.send_message("Message deleted", ephemeral=True)
    
    @app_commands.default_permissions(ban_members=True)
    async def contextban(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Ban")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** banned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(user, reason=reason)
        except Exception:
            await interaction.followup.send(f"Cannot ban {user.display_name}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been banned {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has been banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.display_name} has been banned.", ephemeral=True)
    
    @app_commands.default_permissions(ban_members=True)
    async def contextsoftban(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Soft-Ban")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** soft-banned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.ban(user)
            await asyncio.sleep(1)
            await interaction.guild.unban(user)
        except Exception:
            await interaction.followup.send(f"Cannot soft-ban {user.display_name}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has been soft-banned, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.display_name} has been soft-banned.", ephemeral=True)
    
    @app_commands.default_permissions(ban_members=True)
    async def contextkick(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Kick")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** kicked **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await interaction.guild.kick(user, reason=reason)
        except Exception:
            await interaction.followup.send(f"Cannot kick {user.display_name}.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been kicked {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        try:
            await user.send(embed=embed2)
        except Exception:
            await interaction.followup.send(f"{user.display_name} has been kicked, but has DMs disabled so i couldn't inform them about being banned.", ephemeral=True)
            return
        await interaction.followup.send(f"{user.display_name} has been kicked.", ephemeral=True)
    
    @app_commands.default_permissions(ban_members=True)
    async def contextwarn(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput(title="Enter Reason for Warning")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** privately warned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        embed2 = discord.Embed(color=0xDE1919, title=f"You have been warned for {reason}")
        embed2.set_author(name="Legion TD 2 Discord Server", icon_url="https://cdn.legiontd2.com/icons/DefaultAvatar.png")
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        try:
            await user.send(embed=embed2)
        except Exception:
            #PUBLIC WARN
            embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** publicly warned **{user.display_name}**"
                                                              f"\n**User id**: {user.id}\n**Reason:** {reason}")
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            await modlogs.send(embed=embed)
            botmsgs = await self.bot.fetch_channel(channel_ids["public_warn"])
            await botmsgs.send(f"{user.mention} you have been warned.")
            await interaction.followup.send(f"{user.display_name} has publicly been warned.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"{user.display_name} has been privately warned.", ephemeral=True)
    
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
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** sent a proxy message to {message.channel.mention}"
                                                          f"\n**Message link:**{message_data.jump_url}"
                                                          f"\n**Message content:**\n{proxy_reply}")
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.followup.send(f"Message has been sent.", ephemeral=True)


async def setup(bot:commands.Bot):
    await bot.add_cog(ContextDelete(bot))