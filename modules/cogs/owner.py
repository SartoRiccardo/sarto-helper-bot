import re
import discord
import importlib
import subprocess
import modules.data
import modules.data.owner
from discord.ext import commands
import modules.embeds.help
import aiofiles
from typing import Optional, Literal
CogHelpEmbed = modules.embeds.help.CogHelpEmbed
ConfigHelpEmbed = modules.embeds.help.ConfigHelpEmbed
pgsql = modules.data


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class Owner(commands.Cog):
    ERROR_MESSAGE = "**ERROR:** {} - {}"

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        try:
            importlib.reload(modules.data.owner)
            importlib.reload(modules.embeds.help)
        except:
            pass

    @commands.group(aliases=["cogs"])
    @commands.is_owner()
    async def cog(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=CogHelpEmbed())

    @cog.command(aliases=["add"])
    @commands.is_owner()
    async def load(self, ctx, name):
        try:
            await self.bot.load_extension(f"modules.cogs.{name}")
            await ctx.message.add_reaction(SUCCESS_REACTION)
        except Exception as e:
            await ctx.send(self.ERROR_MESSAGE.format(type(e).__name__, e))

    @cog.command(aliases=["remove"])
    @commands.is_owner()
    async def unload(self, ctx, name):
        try:
            if f"modules.cogs.{name}" != __name__:
                await self.bot.unload_extension(f"modules.cogs.{name}")
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
            await self.bot.unload_extension(f"modules.cogs.{name}")
            await self.bot.load_extension(f"modules.cogs.{name}")
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
    async def sync(self, ctx: discord.ext.commands.Context, where: Optional[Literal["."]] = None) -> None:
        if where == ".":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        else:
            synced = await ctx.bot.tree.sync()
            self.bot.synced_tree = synced
        await ctx.send(f"Synced {len(synced)} commands ({'globally' if where is None else 'here'}).")

    @commands.command()
    @commands.is_owner()
    async def config(self, ctx, key=None, *args):
        special_procedures = {
            "list": self.config_list,
            None: self.config_help,
            "help": self.config_help,
            "remove": self.config_remove,
            "unset": self.config_remove,
            "delete": self.config_remove,
        }
        if key in special_procedures.keys():
            await special_procedures[key](ctx, *args)
            return

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

    @staticmethod
    async def config_help(ctx, *args):
        await ctx.send(embed=ConfigHelpEmbed())
        return

    @staticmethod
    async def config_list(ctx, *args):
        keys = await pgsql.owner.get_all_config_keys()
        keys = [f"`{k['name']}`" for k in keys]
        await ctx.send(", ".join(keys))

    @staticmethod
    async def config_remove(ctx, key, *args):
        print(key, args)
        await pgsql.owner.del_config(key)
        await ctx.message.add_reaction(SUCCESS_REACTION)

    @commands.group()
    @commands.is_owner()
    async def server(self, ctx):
        if ctx.invoked_subcommand is None:
            # await ctx.send(embed=ServerHelpEmbed())
            pass

    @server.command()
    @commands.is_owner()
    async def ram(self, ctx):
        cmd = "ps -o pid,%mem,command ax | sort -b -k3 -r"
        to_check = ["multirole", "sarto-helper-bot", "reditor-srv", "discordbooru", "mizuchi", "pixivcord"]
        out = subprocess.check_output(cmd, shell=True).decode()
        out = re.compile(r" +").sub(" ", out)

        message = "```\n" + \
                  " P.ID     |  %MEM  |  PROCESS"
        for ln in out.split("\n"):
            ln = ln.strip()
            for c in to_check:
                if c in ln:
                    message += "\n" + self.format_ps(ln)
                    break
        message += "\n```"
        await ctx.send(message)

    @staticmethod
    def format_ps(ps_str):
        pid, mem, process = ps_str.split(" ", 2)
        return f"{pid:<8}  |  {mem:<4}  |  {process}"

    @commands.command()
    @commands.is_owner()
    async def traceback(self, ctx):
        fin = await aiofiles.open("nohup.out")
        buffer = [""] * 20
        i = 0
        async for ln in fin:
            buffer[i] = ln
            i = (i+1) % len(buffer)
        await fin.close()

        traceback_str = "".join(buffer[i:] + buffer[0:i])
        if len(traceback_str) > 0:
            await ctx.send(f"```\n{traceback_str[:1900]}\n```")
        else:
            await ctx.message.add_reaction("❌")


async def setup(bot):
    await bot.add_cog(Owner(bot))
