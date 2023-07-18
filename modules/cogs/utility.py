from discord.ext import commands
from modules.util.req import pixabay_search
import discord


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hr(self, ctx, *args):
        await ctx.message.delete()
        await ctx.channel.send("```\n \n```")

    @discord.app_commands.command(name="pixabay", description="Search Pixabay.")
    @discord.app_commands.describe(query="The Pixabay query.")
    async def pixabay(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        results = (await pixabay_search(query))[:5]
        if len(results) == 0:
            await interaction.edit_original_response(
                content="No results found!"
            )
            return
        await interaction.edit_original_response(
            content="\n".join([f"{i}. {results[i]}" for i in range(len(results))])
        )



async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
