from discord.ext import commands


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hr(self, ctx, *args):
        await ctx.message.delete()
        await ctx.channel.send("```\n \n```")


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
