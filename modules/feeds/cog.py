import discord
from discord.ext import commands
import modules.embeds.help
FeedsHelpEmbed = modules.embeds.help.FeedsHelpEmbed


class Feeds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def feed(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=FeedsHelpEmbed())

    @feed.command(aliases=["ls"])
    @commands.has_role("Feed Manager")
    async def list(self, ctx):
        pass

    @feed.command()
    @commands.has_role("Feed Manager")
    async def new(self, ctx):
        pass

    @feed.command(aliases=["delete", "remove"])
    @commands.has_role("Feed Manager")
    async def _delete(self, ctx):
        pass

    @feed.command()
    @commands.has_role("Feed Manager")
    async def edit(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Feeds(bot))
