import discord

def create_mod_log_embed(mod: discord.User, action: str, user: discord.User | discord.Member, reason: str, duration = None):
    return discord.Embed(color=0xDE1919,
                         description=f"**{mod.display_name}** {action} **{user.mention}**"
                                     f"{f"\n**Duration:** {duration}" if duration else f""}"
                                     f"\n**Username:** {user.name} **User id:** {user.id}\n**Reason:** {reason}"
                         )