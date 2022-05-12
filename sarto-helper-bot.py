#!/usr/bin/env python3
import config
import discord
import asyncio
import modules.data.connection
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

DEFAULT_PREFIX = "," if not hasattr(config, "PREFIX") else config.PREFIX
bot = commands.Bot(command_prefix=DEFAULT_PREFIX, intents=intents)


async def main():
    async with bot:
        await modules.data.connection.start()

        bot.remove_command("help")
        await bot.load_extension("modules.cogs.owner")

        cogs = ["feeds", "edopro", "reditor", "reditor_bg", "thumbnail", "utility"]
        for cog in cogs:
            try:
                await bot.load_extension(f"modules.cogs.{cog}")
            except discord.ext.commands.errors.ExtensionNotFound as e:
                print(f"Could not load {e.name}")
        await bot.start(config.TOKEN)


if __name__ == '__main__':
    asyncio.run(main())
