import discord
from discord.ext import tasks
import asyncio
import os
import praw
import subprocess
from datetime import datetime, timedelta
import modules.data as pgsql
import modules.util as util
from random import randint
from discord.ext import commands
from config import REDDIT_AGENT, REDDIT_ID, REDDIT_SECRET


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class REditorCog(commands.Cog):
    TIME_KEY = "rdt_last-loop-bot"
    CHECK_EVERY = 60*60*12

    def __init__(self, bot):
        self.bot = bot
        self.last_checked = None
        evt_loop = asyncio.get_event_loop()
        asyncio.ensure_future(self.init(), loop=evt_loop)

    async def init(self):
        self.last_checked = await self.get_last_time()
        self.threads.start()

    def cog_unload(self):
        self.threads.stop()

    @staticmethod
    async def get_last_time():
        last_time = await pgsql.owner.get_config(REditorCog.TIME_KEY)
        if last_time is None:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            await pgsql.owner.set_config(REditorCog.TIME_KEY, now_str)
            return now

        return datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")

    @staticmethod
    async def set_last_time(time):
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        await pgsql.owner.set_config(REditorCog.TIME_KEY, time_str)

    @commands.group(invoke_without_command=True)
    async def reditor(self, ctx, *args):
        if ctx.invoked_subcommand is None and len(args) == 0:
            # await ctx.send(embed=EdoProHelpEmbed())
            return

    @reditor.command()
    @commands.is_owner()
    async def status(self, ctx):
        out = subprocess.check_output('ps -aux | grep reditor-srv.py', shell=True)
        if len(out.decode().split("\n")) == 4:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")

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
    @commands.is_owner()
    async def force(self):
        self.last_checked += timedelta(days=100)

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
        titles = []
        n = 1
        for submission in reddit.subreddit("askreddit").hot(limit=10):
            message += f"{n} `⬆️ {submission.score}` {submission.title}\n"
            n += 1
            threads.append(submission.id)
            titles.append(submission.title)
        return threads, titles, message

    @tasks.loop(seconds=30)
    async def threads(self):
        if datetime.now() < (self.last_checked + timedelta(seconds=REditorCog.CHECK_EVERY)):
            return
        self.last_checked = datetime.now()
        await self.set_last_time(self.last_checked)

        await pgsql.reditor.remove_old_threads()

        threads, titles, message = REditorCog.get_askreddit()
        print(threads)
        duplicates = await pgsql.reditor.get_existing_threads(threads)
        threads = [id for id in threads if id not in duplicates]
        if len(threads) == 0:
            return

        embed = discord.Embed(
            title="Threads of today",
            description=message,
            color=discord.colour.Colour.purple()
        )

        threads = [(threads[i], titles[i]) for i in range(len(threads))]
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

        threads = [threads[i] + (message.id, i) for i in range(len(threads))]
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
        thumbnail_channel = discord.utils.get(category.text_channels, name="thumbnails")
        if not thumbnail_channel or not thread_channel or thread_channel.id != payload.channel_id:
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

        threads = await pgsql.reditor.get_threads(payload.message_id, filter=chosen_threads)
        messages = []
        for t in threads:
            messages.append(
                await thumbnail_channel.send(f"Reply with a title and a thumbnail for **{t['title']}**")
            )
        await pgsql.reditor.choose_threads(
            [(threads[i]["id"], messages[i].id) for i in range(len(threads))]
        )

    def is_thumbnail_channel(self, guild_id, channel_id):
        guild = discord.utils.get(self.bot.guilds, id=guild_id)
        category = discord.utils.get(guild.categories, name="reditor")
        if not category:
            return
        channel = discord.utils.get(category.text_channels, name="thumbnails")
        return channel and channel.id == channel_id

    @commands.Cog.listener()
    async def on_message(self, message):
        if len(message.attachments) == 0 or \
                message.reference is None or \
                not self.is_thumbnail_channel(message.reference.guild_id, message.reference.channel_id):
            return
        reply_id = message.reference.message_id
        title = message.content
        thumbnail = message.attachments[0].url
        await pgsql.reditor.set_video_meta(reply_id, title, thumbnail)
        await message.add_reaction("✅")

    @reditor.command()
    async def thumbnail(self, ctx, *thumbnail_text):
        if len(ctx.message.attachments) == 0:
            await ctx.send("You must attach an image!")
        thumb_img_url = ctx.message.attachments[0].url
        if not (thumb_img_url.endswith(".png") or thumb_img_url.endswith(".jpg")):
            await ctx.send("You must attach an image!")
        thumb_text = " ".join(thumbnail_text)

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        util.requests.download_file(thumb_img_url, source_path)
        util.image.make_thumbnail(thumb_text, source_path, dest_path)

        fp = open(dest_path, "rb")
        await ctx.send(file=discord.File(fp, filename="thumbnail.png"))
        fp.close()
        if os.path.exists(source_path):
            os.remove(source_path)
        if os.path.exists(dest_path):
            os.remove(dest_path)


def setup(bot):
    bot.add_cog(REditorCog(bot))
