import asyncio
import json
import discord
from discord import app_commands, ui, Interaction
from discord._types import ClientT
from discord.ext import commands
import cogs.moderation

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class ContextInput(ui.Modal, title='Enter reason for punishment'):
    answer = ui.TextInput(label='Reason', style=discord.TextStyle.short)
    
    async def on_submit(self, interaction: Interaction[ClientT], /) -> None:
        await interaction.response.defer()


class ContextDelete(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='Delete Message',
            callback=self.delete
        )
        self.ctx_menu2 = app_commands.ContextMenu(
            name='Ban User',
            callback=self.contextban
        )
        self.bot.tree.add_command(self.ctx_menu)
        self.bot.tree.add_command(self.ctx_menu2)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)
        self.bot.tree.remove_command(self.ctx_menu2.name, type=self.ctx_menu.type)
    
    @app_commands.checks.has_permissions(ban_members=True)
    async def delete(self, interaction: discord.Interaction, message: discord.Message):
        await message.delete()
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** deleted a message from **{message.author.display_name}**"
                                                          f"\n**User id**: {message.author.id}"
                                                          f"\n**Channel**: {message.channel.name}"
                                                          f"\n**Message content:**\n{message.content}")
        channel_ids = cogs.moderation.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.response.send_message("Message deleted", ephemeral=True)
    
    @app_commands.checks.has_permissions(ban_members=True)
    async def contextban(self, interaction: discord.Interaction, user: discord.User):
        context_modal = ContextInput()
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        reason = context_modal.answer.value
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** banned **{user.display_name}**"
                                                          f"\n**User id**: {user.id}\n**Reason:** {reason}")
        channel_ids = cogs.moderation.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        await interaction.guild.ban(user, reason=reason)
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


async def setup(bot:commands.Bot):
    await bot.add_cog(ContextDelete(bot))