import json
import os
import discord
from discord.ext import commands
import logging

from cogs.event_listeners import setup_persistent_views

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
discord.utils.setup_logging(handler=handler, level=logging.INFO, root=False)

with open('Files/json/Secrets.json') as f:
    secret_file = json.load(f)
    f.close()

class Legion(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="?", intents=intents)
        self.exts = []
        self.guild_id = secret_file["guild_id"]
        for e in os.listdir("cogs"):
            if "__pycache__" in e:
                continue
            elif "cog_template" in e:
                continue
            self.exts.append("cogs." + e.split(".")[0])
    
    async def setup_hook(self) -> None:
        for extension in self.exts:
            await self.load_extension(extension)
    
    async def on_ready(self):
        await setup_persistent_views(self)
        print(f'"{self.user.display_name}" is now running!')
        game = discord.CustomActivity("Direct Message for Mod Mail")
        await self.change_presence(activity=game)


if __name__ == "__main__":
    client = Legion()
    client.run(secret_file["token"])
