#!/usr/bin/env python3
import config
import discord
import modules.data.connection
from discord.ext import commands


DEFAULT_PREFIX = "," if not hasattr(config, "PREFIX") else config.PREFIX


class SartoHelperBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix=DEFAULT_PREFIX,
            intents=intents,
            application_id=config.APP_ID,
        )
        self.default_embed_color = discord.Color.dark_magenta()
        self.remove_command("help")

    async def setup_hook(self):
        await modules.data.connection.start()
        await self.load_extension("modules.cogs.owner")

        cogs = ["feeds", "edopro", "reditor", "reditor_bg", "thumbnail", "utility", "btd6"]
        for cog in cogs:
            try:
                await self.load_extension(f"modules.cogs.{cog}")
            except discord.ext.commands.errors.ExtensionNotFound as e:
                print(f"Could not load {e.name}")
            except Exception as e:
                print(e)
                print(f"Could not load {e.name}")


if __name__ == '__main__':
    SartoHelperBot().run(config.TOKEN)
