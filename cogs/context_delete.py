import json
import discord
from discord import app_commands
from discord.ext import commands

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
                                                          f"\n**Message content:**\n{message.content}")
        channel = await self.bot.fetch_channel(secret_file["modlogsid"])
        await channel.send(embed=embed)
        await interaction.response.send_message("Message deleted", ephemeral=True)

async def setup(bot:commands.Bot):
    await bot.add_cog(ContextDelete(bot))