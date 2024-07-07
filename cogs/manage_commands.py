import traceback
import concurrent.futures
import functools
import asyncio
from discord.ext import commands
import os
from datetime import datetime


class ManageCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
    
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
                        await self.client.reload_extension(extension)
                    print("Reloaded: " + ",".join(new_exts))
                else:
                    await self.client.reload_extension("cogs." + content.lower())
                    print("Reloaded: " + content)
            except Exception:
                traceback.print_exc()
    
    @commands.command()
    async def sync(self, ctx: commands.Context):
        if ctx.author.name == "drachir_":
            print(await self.client.tree.sync(guild=None))

async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCommands(bot))