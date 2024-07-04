import json
import discord
from discord import app_commands
from discord.ext import commands
import cogs.moderation

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class ContextDelete(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='Delete Message',
            callback=self.delete
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)
    
    @app_commands.checks.has_permissions(ban_members=True)
    async def delete(self, interaction: discord.Interaction, message: discord.Message):
        await message.delete()
        embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.display_name}** deleted a message from **{message.author.display_name}**"
                                                          f"\n**User id**: {message.author.id}"
                                                          f"\n**Message content:**\n{message.content}")
        channel_ids = cogs.moderation.get_channels(interaction.guild.id)
        if not channel_ids:
            await interaction.followup.send(f"Channel setup not done yet, use /setup.", ephemeral=True)
            return
        modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
        await modlogs.send(embed=embed)
        await interaction.response.send_message("Message deleted", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(ContextDelete(bot))