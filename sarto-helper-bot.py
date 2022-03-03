#!/usr/bin/env python3
import config
import discord
import asyncio
import modules.data.connection
from discord.ext import commands

DEFAULT_PREFIX = "," if not hasattr(config, "PREFIX") else config.PREFIX
bot = commands.Bot(command_prefix=DEFAULT_PREFIX)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(modules.data.connection.start())

    bot.remove_command("help")
    bot.load_extension("modules.cogs.owner")

    cogs = ["feeds", "edopro", "reditor", "thumbnail"]
    for cog in cogs:
        try:
            bot.load_extension(f"modules.cogs.{cog}")
        except discord.ext.commands.errors.ExtensionNotFound as e:
            print(f"Could not load {e.name}")

    bot.run(config.TOKEN)
