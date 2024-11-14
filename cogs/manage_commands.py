import json
import traceback
import concurrent.futures
import functools
import asyncio
from discord.ext import commands
import os
from datetime import datetime


class ManageCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.command()
    async def reload(self, ctx: commands.Context):
        if ctx.author.name == "drachir_":
            try:
                content = ctx.message.content[8:]
                if content.casefold() == "all":
                    new_exts = []
                    for e in os.listdir("cogs"):
                        if "__pycache__" in e:
                            continue
                        elif "cog_template" in e:
                            continue
                        new_exts.append("cogs." + e.split(".")[0])
                    for extension in new_exts:
                        await self.bot.reload_extension(extension)
                    print("Reloaded: " + ",".join(new_exts))
                else:
                    await self.bot.reload_extension("cogs." + content.lower())
                    print("Reloaded: " + content)
            except Exception:
                traceback.print_exc()
    
    @commands.command()
    async def sync(self, ctx: commands.Context):
        if ctx.author.name == "drachir_":
            print(await self.bot.tree.sync(guild=None))
    
    # @commands.command()
    # async def create_roles(self, ctx: commands.Context):
    #     if ctx.author.name == "drachir_":
    #         rank_emotes = {
    #             "Unranked": "<:Unranked:1299633644746444830>",
    #             "Bronze": "<:Bronze:1299633629802139709>",
    #             "Silver": "<:Silver:1299633694662856705>",
    #             "Gold": "<:Gold:1299633634596098078>",
    #             "Platinum": "<:Platinum:1299633639788777544>",
    #             "Diamond": "<:Diamond:1299633630695522327>",
    #             "Expert": "<:Expert:1299633632650199091>",
    #             "Master": "<:Master:1299633638534811659>",
    #             "SeniorMaster": "<:SeniorMaster:1299633641051394109>",
    #             "Grandmaster": "<:GrandMaster:1299633635431022657>",
    #             "Legend": "<:Legend:1299633637049761792>"
    #         }
    #         with open("Files/json/rank_roles.json", "r") as config_file:
    #             config = json.load(config_file)
    #         GUILD_ID = config["GUILD_ID"]
    #         guild = self.bot.get_guild(GUILD_ID)
    #         for i, rank in enumerate(rank_emotes):
    #             await asyncio.sleep(1)
    #             await guild.create_role(name=rank)

async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCommands(bot))