import discord
import subprocess
from discord.ext import commands


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class EdoProCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def edopro(self, ctx, *args):
        if ctx.invoked_subcommand is None and len(args) == 0:
            # await ctx.send(embed=EdoProHelpEmbed())
            return

    @edopro.command()
    @commands.is_owner()
    async def status(self, ctx):
        out = subprocess.check_output('ps -aux | grep edopro', shell=True)
        if len(out.decode().split("\n")) == 4:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")


def setup(bot):
    bot.add_cog(EdoProCog(bot))
