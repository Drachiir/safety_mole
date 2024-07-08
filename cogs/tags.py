import difflib
import json
import os.path
import pathlib
from pathlib import Path
import discord
from discord import app_commands, ui
from discord.ext import commands
import cogs.moderation as modcog

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()


class ContextInput(ui.Modal):
    answer = ui.TextInput(label='Tag Name', style=discord.TextStyle.short)
    
    async def on_submit(self, interaction) -> None:
        await interaction.response.defer()

class Tags(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_create_tag = app_commands.ContextMenu(name='Create Tag', callback=self.create_tag)
        # Add commands to command tree
        self.bot.tree.add_command(self.ctx_create_tag)
    
    def cog_load(self):
        tree = self.bot.tree
        self._old_tree_error = tree.on_error
        tree.on_error = self.on_app_command_error
    
    async def cog_unload(self) -> None:
        tree = self.bot.tree
        tree.on_error = self._old_tree_error
        self.bot.tree.remove_command(self.ctx_create_tag.name, type=self.ctx_create_tag.type)
    
    @app_commands.guild_only()
    @app_commands.checks.has_any_role("Community Helper", "Moderator", "Developer")
    async def create_tag(self, interaction: discord.Interaction, message: discord.Message):
        context_modal = ContextInput(title="Enter the name for the Tag")
        await interaction.response.send_modal(context_modal)
        await context_modal.wait()
        tag_name = context_modal.answer.value.lower()
        path = str(pathlib.Path(__file__).parent.parent.resolve()) + f"/Files/Tags/{interaction.guild.id}"
        if not Path(Path(str(path))).is_dir():
            print(interaction.guild.name + ' Guild tag folder not found, creating new one...')
            Path(str(path)).mkdir(parents=True, exist_ok=True)
        if os.path.isfile(path + f"/{tag_name}.txt"):
            await interaction.followup.send(f"Tag under name {tag_name} already exists.", ephemeral=True)
            return
        with open(path + f"/{tag_name}.txt", "w") as f:
            f.write(message.content)
        await interaction.followup.send(f"Tag under name {tag_name} created.", ephemeral=True)
        channel_ids = modcog.get_channels(interaction.guild.id)
        if not channel_ids:
            return
        else:
            embed = discord.Embed(color=0xDE1919, description=f"**{interaction.user.mention}** created tag '**{tag_name}**'"
                                                              f"\n**Tag Source:** {message.jump_url}")
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            await modlogs.send(embed=embed)
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        await interaction.response.send_message("You don't have permission to use this.", ephemeral=True)
    
    @commands.guild_only()
    @commands.command()
    async def tag(self, ctx: commands.Context):
        path = str(pathlib.Path(__file__).parent.parent.resolve()) + f"/Files/Tags/{ctx.guild.id}"
        if not Path(Path(str(path))).is_dir():
            await ctx.send("No tags found for this server.")
        tag_list = os.listdir(path)
        command_input = ctx.message.content[5:].lower()
        try:
            with open(path + f"/{command_input}.txt", "r") as f:
                tag_content = f.read()
        except Exception:
            close_matches = difflib.get_close_matches(f"{command_input}.txt", tag_list, cutoff=0.7, n=5)
            if len(close_matches) == 0:
                embed3 = discord.Embed(color=0xDE1919, description=f"Tag '{command_input}' not found.")
                await ctx.send(embed=embed3)
                return
            output_string = f"**Tag '{command_input}' not found.\nDo you mean:**\n"
            for match in close_matches:
                output_string += f"`?tag {match.replace(".txt", "")}`\n"
            embed = discord.Embed(color=0xDE1919, description=output_string)
            await ctx.send(embed=embed)
            return
        await ctx.send(tag_content)
    
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    @commands.command()
    async def tag_delete(self, ctx: commands.Context):
        path = str(pathlib.Path(__file__).parent.parent.resolve()) + f"/Files/Tags/{ctx.guild.id}"
        if not Path(Path(str(path))).is_dir():
            await ctx.send("No tags found for this server.")
        tag_list = os.listdir(path)
        command_input = ctx.message.content[12:].lower()
        try:
            os.remove(path + f"/{command_input}.txt")
        except Exception:
            close_matches = difflib.get_close_matches(f"{command_input}.txt", tag_list, cutoff=0.6, n=5)
            if len(close_matches) == 0:
                await ctx.send(f"Tag '{command_input}' not found.")
                return
            output_string = f"**Tag '{command_input}' not found.\nDo you mean:**\n"
            for match in close_matches:
                output_string += f"`?tag {match.replace(".txt", "")}`\n"
            embed = discord.Embed(color=0xDE1919, description=output_string)
            await ctx.send(embed=embed)
            return
        await ctx.send(f"Tag '{command_input}' deleted.")
        channel_ids = modcog.get_channels(ctx.guild.id)
        if not channel_ids:
            return
        else:
            embed = discord.Embed(color=0xDE1919, description=f"**{ctx.author.mention}** deleted tag '**{command_input}**'")
            modlogs = await self.bot.fetch_channel(channel_ids["mod_logs"])
            await modlogs.send(embed=embed)
    
    @tag_delete.error
    async def on_tag_delete_error(self, ctx: commands.Context, error: commands.CommandError):
        pass
        
        
async def setup(bot:commands.Bot):
    await bot.add_cog(Tags(bot))