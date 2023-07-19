import os
import shutil
import discord
from discord.ext import commands
import modules.data
pgsql = modules.data


class Btd6Cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="lb-zip",
                                  description="get the ZIP file of the latest event's leaderboard.")
    async def lbzip(self, interaction: discord.Interaction) -> None:
        lb_path = await pgsql.owner.get_config("btd6_lb-tracker-path")
        if lb_path is None:
            await interaction.response.send_message(
                content="`btd6_lb-tracker-path` is not set!"
            )
        latest_edited = {"path": "sarto-helper-bot.py", "edited_at": 0}
        for file in os.listdir(lb_path):
            path = f"{lb_path}/{file}"
            if os.path.isdir(path) and os.path.getctime(path) > latest_edited["edited_at"]:
                latest_edited = {"path": file, "edited_at": os.path.getctime(path)}

        shutil.make_archive("leaderboard", "zip",
                            root_dir=lb_path,
                            base_dir=latest_edited["path"])
        await interaction.response.send_message(
            file=discord.File("leaderboard.zip")
        )
        os.remove("leaderboard.zip")


async def setup(bot):
    await bot.add_cog(Btd6Cog(bot))
