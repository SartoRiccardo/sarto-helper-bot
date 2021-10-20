#!/usr/bin/env python3
import config
import discord
import asyncio
import modules.data.connection
from discord.ext import commands

DEFAULT_PREFIX = ","
bot = commands.Bot(command_prefix=DEFAULT_PREFIX)


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(modules.data.connection.start())

    bot.remove_command("help")
    bot.load_extension("modules.owner.cog")

    cogs = ["modules.feeds.cog"]
    for cog in cogs:
        bot.load_extension(cog)

    bot.run(config.TOKEN)
