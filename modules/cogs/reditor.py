import discord
import asyncio
import praw
import subprocess
import modules.data as pgsql
from discord.ext import commands
from config import REDDIT_AGENT, REDDIT_ID, REDDIT_SECRET


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class REditorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def reditor(self, ctx, *args):
        if ctx.invoked_subcommand is None and len(args) == 0:
            # await ctx.send(embed=EdoProHelpEmbed())
            return

    # @reditor.command()
    # @commands.is_owner()
    # async def status(self, ctx):
    #     out = subprocess.check_output('ps -aux | grep reditor', shell=True)
    #     if len(out.decode().split("\n")) == 4:
    #         await ctx.message.add_reaction("✅")
    #     else:
    #         await ctx.message.add_reaction("❌")

    @reditor.command()
    async def setup(self, ctx):
        """
        Create the category "reditor";
        Create the channels "#log", "#threads", and "#thumbnails";
        Create the webhook "REditor Logger".
        """
        category = await ctx.guild.create_category("reditor")

        log_channel = await category.create_text_channel("log")
        webhook = await log_channel.create_webhook(name="REditor Logger")

        channels = ["threads", "thumbnails"]
        await asyncio.wait(
            [category.create_text_channel(c) for c in channels] +
            [pgsql.owner.set_config("rdt_logger", webhook.url)],
            return_when=asyncio.ALL_COMPLETED
        )

    @reditor.command()
    async def forceday(self, ctx):
        await self.threads()

    @staticmethod
    def get_askreddit():
        reddit = praw.Reddit(
            client_id=REDDIT_ID, client_secret=REDDIT_SECRET, user_agent=REDDIT_AGENT,
            check_for_updates="False", comment_kind="t1", message_kind="t4", redditor_kind="t2",
            submission_kind="t3", subreddit_kind="t5", trophy_kind="t6", oauth_url="https://oauth.reddit.com",
            reddit_url="https://www.reddit.com", short_url="https://redd.it"
        )
        reddit.read_only = True

        message = ""
        threads = []
        n = 1
        for submission in reddit.subreddit("askreddit").hot(limit=10):
            message += f"{n} `⬆️ {submission.score}` {submission.title}\n"
            n += 1
            threads.append(submission.id)
        return threads, message

    async def threads(self):
        await pgsql.reditor.remove_old_threads()

        threads, message = REditorCog.get_askreddit()
        duplicates = await pgsql.reditor.get_existing_threads(threads)
        threads = [id for id in threads if id not in duplicates]
        if len(threads) == 0:
            return

        embed = discord.Embed(
            title="Threads of today",
            description=message,
            color=discord.colour.Colour.purple()
        )

        for g in self.bot.guilds:
            category = discord.utils.get(g.categories, name="reditor")
            if not category:
                continue
            await self.post_threads(category, embed, threads)

    @staticmethod
    async def post_threads(category, embed, threads):
        thread_channel = discord.utils.get(category.text_channels, name="threads")
        if not thread_channel:
            return

        message = await thread_channel.send(f"Today's threads:\n", embed=embed)
        reactions = ["1️⃣", "2️⃣",  "3️⃣",  "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "✅"]
        for r in reactions:
            await message.add_reaction(r)

        threads = [(threads[i], message.id, i) for i in range(len(threads))]
        await pgsql.reditor.add_threads(threads)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if str(payload.emoji) != "✅":
            return

        guild = discord.utils.get(self.bot.guilds, id=payload.guild_id)
        if guild.owner_id != payload.user_id:
            return

        category = discord.utils.get(guild.categories, name="reditor")
        if not category:
            return

        thread_channel = discord.utils.get(category.text_channels, name="threads")
        if not thread_channel or thread_channel.id != payload.channel_id:
            return

        message = discord.utils.get(
            await thread_channel.history(limit=7).flatten(),
            id=payload.message_id
        )
        if not message:
            return

        chosen_threads = []
        for i in range(len(message.reactions)):
            r = message.reactions[i]
            if r.count > 1:
                chosen_threads.append(i)
        await message.clear_reactions()

        await pgsql.reditor.choose_threads(
            await pgsql.reditor.get_threads(payload.message_id, filter=chosen_threads)
        )


def setup(bot):
    bot.add_cog(REditorCog(bot))
