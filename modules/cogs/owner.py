import discord
import importlib
import modules.data
import modules.data.owner
from discord.ext import commands
import modules.embeds.help
CogHelpEmbed = modules.embeds.help.CogHelpEmbed
pgsql = modules.data


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class Owner(commands.Cog):
    ERROR_MESSAGE = "**ERROR:** {} - {}"

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        importlib.reload(modules.data.owner)

    @commands.group()
    @commands.is_owner()
    async def cog(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=CogHelpEmbed())

    @cog.command(aliases=["add"])
    @commands.is_owner()
    async def load(self, ctx, name):
        try:
            self.bot.load_extension(f"modules.cogs.{name}")
            await ctx.message.add_reaction(SUCCESS_REACTION)
        except Exception as e:
            await ctx.send(self.ERROR_MESSAGE.format(type(e).__name__, e))

    @cog.command(aliases=["remove"])
    @commands.is_owner()
    async def unload(self, ctx, name):
        try:
            if f"modules.cogs.{name}" != __name__:
                self.bot.unload_extension(f"modules.cogs.{name}")
                await ctx.message.add_reaction(SUCCESS_REACTION)
            else:
                await ctx.send(
                    f"You cannot unload the `{name}` cog. Did you mean `,cog reload {name}`?"
                )
        except Exception as e:
            await ctx.send(self.ERROR_MESSAGE.format(type(e).__name__, e))

    @cog.command()
    @commands.is_owner()
    async def reload(self, ctx, name):
        try:
            self.bot.unload_extension(f"modules.cogs.{name}")
            self.bot.load_extension(f"modules.cogs.{name}")
            await ctx.message.add_reaction(SUCCESS_REACTION)
        except Exception as e:
            await ctx.send(self.ERROR_MESSAGE.format(type(e).__name__, e))

    @cog.command(alias=["list"])
    @commands.is_owner()
    async def list(self, ctx):
        cogs = [str_cog for str_cog in self.bot.cogs]
        await ctx.send("Loaded cogs: " + ", ".join(cogs))

    @commands.command()
    @commands.is_owner()
    async def config(self, ctx, key, *args):
        new_value = None
        if args:
            new_value = " ".join(args)

        if new_value:
            await pgsql.owner.set_config(key, new_value)
            await ctx.message.add_reaction(SUCCESS_REACTION)
        else:
            value = await pgsql.owner.get_config(key)
            if value is None:
                await ctx.send(f"Variable `{key}` is unset.")
            else:
                await ctx.send(f"Variable `{key}` is set to `{value}`.")


def setup(bot):
    bot.add_cog(Owner(bot))
