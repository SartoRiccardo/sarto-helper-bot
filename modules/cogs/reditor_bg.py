import os
import discord
import asyncio
import asyncpraw
import importlib
from datetime import datetime, timedelta
from discord.ext import commands, tasks
import modules.data
import modules.data.owner
import modules.data.reditor
import modules.util
from config import REDDIT_AGENT, REDDIT_ID, REDDIT_SECRET
pgsql = modules.data
util = modules.util


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class REditorTasksCog(commands.Cog):
    TIME_KEY = "rdt_last-loop-bot"
    CHECK_EVERY = 60*60*12

    def __init__(self, bot):
        self.bot = bot
        self.last_checked = None

    async def cog_load(self):
        self.last_checked = await self.get_last_time()
        # self.daily_threads.start()
        self.update_video_status.start()
        self.delete_exported_threads.start()

    async def cog_unload(self):
        importlib.reload(modules.data.reditor)
        importlib.reload(modules.data.owner)
        importlib.reload(modules.util.logger)
        importlib.reload(modules.util.image)
        importlib.reload(util)
        importlib.reload(pgsql)
        self.daily_threads.stop()
        self.update_video_status.stop()
        self.delete_exported_threads.stop()

    @staticmethod
    async def get_last_time():
        last_time = await pgsql.owner.get_config(REditorTasksCog.TIME_KEY)
        if last_time is None:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            await pgsql.owner.set_config(REditorTasksCog.TIME_KEY, now_str)
            return now

        return datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")

    async def set_last_time(self, time):
        self.last_checked = time
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        await pgsql.owner.set_config(REditorTasksCog.TIME_KEY, time_str)

    @staticmethod
    async def get_askreddit(subreddit):
        reddit = asyncpraw.Reddit(
            client_id=REDDIT_ID, client_secret=REDDIT_SECRET, user_agent=REDDIT_AGENT,
            check_for_updates="False", comment_kind="t1", message_kind="t4", redditor_kind="t2",
            submission_kind="t3", subreddit_kind="t5", trophy_kind="t6", oauth_url="https://oauth.reddit.com",
            reddit_url="https://www.reddit.com", short_url="https://redd.it"
        )
        reddit.read_only = True

        threads = []
        async for submission in (await reddit.subreddit(subreddit)).hot(limit=20):
            threads.append({
                "id": submission.id,
                "title": submission.title,
                "score": submission.score
            })
        return threads

    @tasks.loop(seconds=30)
    async def daily_threads(self):
        if datetime.now() < (self.last_checked + timedelta(seconds=REditorTasksCog.CHECK_EVERY)):
            return
        await self.set_last_time(datetime.now())

        await pgsql.reditor.remove_old_threads()

        subs_to_check = ["askreddit", "askmen"]
        for sub in subs_to_check:
            await self.send_hot_threads(sub)

    async def send_hot_threads(self, sub):
        threads = await REditorTasksCog.get_askreddit(sub)
        debug_msg = f"Threads gotten: `{'`, `'.join([t['id'] for t in threads])}`\n"
        duplicates = await pgsql.reditor.get_existing_threads([t['id'] for t in threads])
        debug_msg += f"Dupe threads: `{'`, `'.join(duplicates)}`\n"
        threads = [t for t in threads if t["id"] not in duplicates][:10]
        debug_msg += f"Final threads: `{'`, `'.join([t['id'] for t in threads])}`\n"
        await util.logger.Logger.log(debug_msg, util.logger.Logger.DEBUG)
        if len(threads) == 0:
            return

        message = ""
        score_len = len(str(max([t['score'] for t in threads])))  # Get the digit number of the highest score
        msg_template = "{}. `^ {:<" + str(score_len) + "}` {}\n"
        for i in range(len(threads)):
            t = threads[i]
            message += msg_template.format(i+1, t['score'], t['title'])

        embed = discord.Embed(
            title="Threads of today",
            description=message,
            color=discord.colour.Colour.purple(),
        ).set_footer(text=f"r/{sub}")

        threads = [(threads[i]["id"], threads[i]["title"]) for i in range(len(threads))]
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
        reactions = ["1️⃣", "2️⃣",  "3️⃣",  "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(min(len(reactions), len(threads))):
            r = reactions[i]
            await message.add_reaction(r)
        await message.add_reaction("✅")

        threads = [threads[i] + (message.id, i) for i in range(len(threads))]
        await pgsql.reditor.add_threads(threads)

    @tasks.loop(seconds=30)
    async def update_video_status(self):
        documents = await pgsql.reditor.get_newly_created_videos()

        for doc_id in documents:
            await self.create_video_thread(doc_id)

    async def create_video_thread(self, document_id):
        thumbnail_channel = await self.get_thumbnail_channel()
        if thumbnail_channel is None:
            return

        video = await pgsql.reditor.get_document_info(document_id)
        video_name = video["title"] if video["title"] else video["thread"]
        message = await thumbnail_channel.fetch_message(video["message"])
        video_thread = await message.create_thread(name=video_name)
        await video_thread.add_user(thumbnail_channel.guild.owner)
        await pgsql.reditor.set_video_thread(video["thread"], video_thread.id)

        scenes = await self.get_scenes(video["document_id"])
        message_ids = []
        scene_ids = []
        for scn in scenes:
            scene_message = await video_thread.send(file=discord.File(scn["media"]))
            message_ids.append(scene_message.id)
            scene_ids.append(scn["id"])
        await modules.data.reditor.set_video_scenes(video_thread.id, message_ids, scene_ids)

        await thumbnail_channel.purge(check=lambda msg: msg.type == discord.MessageType.thread_created)

    async def get_thumbnail_channel(self) -> discord.TextChannel:
        for guild in self.bot.guilds:
            category = discord.utils.get(guild.categories, name="reditor")
            if not category:
                continue

            thumbnail_channel = discord.utils.get(category.text_channels, name="thumbnails")
            if not thumbnail_channel:
                continue

            return thumbnail_channel

    @staticmethod
    async def get_scenes(document_id: int):
        """
        TEMPORARY METHOD. Will be overruled by an API call to the REditor server.
        """
        reditor_saves_path = await pgsql.owner.get_config("rdt_saves-path")
        scenes = []
        scenes_path = f"{reditor_saves_path}/{document_id:05d}/scenes"
        if not os.path.exists(scenes_path):
            return scenes

        for directory in os.listdir(scenes_path):
            media_file_name = None
            for file in os.listdir(os.path.join(scenes_path, directory)):
                if file.startswith("media"):
                    media_file_name = file
                    break

            if media_file_name is None:
                continue
            scenes.append({"id": int(directory[-5:]), "media": f"{scenes_path}/{directory}/{media_file_name}"})

        return scenes

    @tasks.loop(seconds=30)
    async def delete_exported_threads(self):
        exported_videos = await pgsql.reditor.get_newly_exported_documents()
        for video in exported_videos:
            await self.delete_video_thread(video)

    async def delete_video_thread(self, document_id):
        thread_id = await pgsql.reditor.get_thread_id(document_id)
        for g in self.bot.guilds:
            thread = discord.utils.get(g.threads, id=thread_id)
            if not thread:
                continue
            await pgsql.reditor.delete_thread(thread_id)
            await thread.delete()

    @commands.is_owner()
    @commands.command()
    async def rmthreads(self, ctx):
        for thread in ctx.channel.threads:
            await thread.delete()


async def setup(bot):
    await bot.add_cog(REditorTasksCog(bot))