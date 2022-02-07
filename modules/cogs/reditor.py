import os
import csv
import discord
import asyncio
import asyncpraw
import importlib
import subprocess
from random import randint
from datetime import datetime, timedelta
from discord.ext import commands, tasks
import modules.data
import modules.data.owner
import modules.data.reditor
import modules.util
from modules.embeds.help import REditorHelpEmbed
from config import REDDIT_AGENT, REDDIT_ID, REDDIT_SECRET
pgsql = modules.data
util = modules.util


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
        self.daily_threads.start()

    def cog_unload(self):
        importlib.reload(modules.data.reditor)
        importlib.reload(modules.data.owner)
        importlib.reload(modules.util.logger)
        importlib.reload(modules.util.image)
        importlib.reload(util)
        importlib.reload(pgsql)
        self.daily_threads.stop()

    @staticmethod
    async def get_last_time():
        last_time = await pgsql.owner.get_config(REditorCog.TIME_KEY)
        if last_time is None:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            await pgsql.owner.set_config(REditorCog.TIME_KEY, now_str)
            return now

        return datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")

    async def set_last_time(self, time):
        self.last_checked = time
        time_str = time.strftime("%Y-%m-%d %H:%M:%S")
        await pgsql.owner.set_config(REditorCog.TIME_KEY, time_str)

    @commands.group(invoke_without_command=True)
    async def reditor(self, ctx, *args):
        if ctx.invoked_subcommand is None and len(args) == 0:
            await ctx.send(embed=REditorHelpEmbed())

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
    async def force(self, ctx):
        await self.set_last_time(
            self.last_checked - timedelta(seconds=REditorCog.CHECK_EVERY*100)
        )
        await ctx.message.add_reaction("✅")

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
        if datetime.now() < (self.last_checked + timedelta(seconds=REditorCog.CHECK_EVERY)):
            return
        await self.set_last_time(datetime.now())

        await pgsql.reditor.remove_old_threads()

        subs_to_check = ["askreddit", "askmen"]
        for sub in subs_to_check:
            await self.send_hot_threads(sub)

    async def send_hot_threads(self, sub):
        threads = await REditorCog.get_askreddit(sub)
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
            await thread_channel.history(limit=14).flatten(),
            id=payload.message_id
        )
        if not message:
            return

        chosen_threads = []
        for i in range(len(message.reactions)):
            r = message.reactions[i]
            if r.count > 1:
                chosen_threads.append(i)
        await util.logger.Logger.log(f"Chosen indexes: {chosen_threads}", util.logger.Logger.DEBUG)
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

        reference = message.reference.cached_message
        if not reference:
            history = await message.channel.history(limit=100).flatten()
            reference = discord.utils.get(history, id=reply_id)
        if reference and reference.author.id == self.bot.user.id and not reference.edited_at:
            await reference.edit(content=reference.content[:39] + reference.content[41:-2])
        await message.add_reaction("✅")

    @reditor.command()
    async def thumbnail(self, ctx, *, thumb_text):
        if len(ctx.message.attachments) == 0:
            # Fallback if no image attached
            if not ctx.message.reference:
                # Use last image sent in the channel by a non-bot user
                thumb_img_url = None
                history = await ctx.channel.history(limit=100).flatten()
                for message in history:
                    if not message.author.bot and len(message.attachments) > 0:
                        thumb_img_url = message.attachments[0].url
                        break
                if not thumb_img_url:
                    await ctx.send("You must attach an image!")
                    return
            else:
                # If replying to a message, use that message's image, if any.
                reference = ctx.message.reference
                if reference.cached_message:
                    message = reference.cached_message
                else:
                    message = discord.utils.get(await ctx.channel.history(limit=100).flatten(), id=reference.message_id)
                    if not message:
                        await ctx.send("Are you replying to a message that's too old? Please send the image again!")
                        return
                thumb_img_url = message.attachments[0].url
        else:
            thumb_img_url = ctx.message.attachments[0].url

        if not (thumb_img_url.endswith(".png") or thumb_img_url.endswith(".jpg")):
            await ctx.send("You must attach an image!")
            return

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.requests.download_file(thumb_img_url, source_path)
        util.image.make_thumbnail(thumb_text, source_path, dest_path)

        fp = open(dest_path, "rb")
        await ctx.send(file=discord.File(fp, filename="thumbnail.png"))
        fp.close()
        if os.path.exists(source_path):
            os.remove(source_path)
        if os.path.exists(dest_path):
            os.remove(dest_path)

    @reditor.command(aliases=["ready"])
    async def available(self, ctx):
        videos_ready = await pgsql.reditor.get_uploadable()
        videos_exportable = await pgsql.reditor.get_exportable()
        if len(videos_ready) == 0:
            message = "There are no videos ready!"
        else:
            message = f"There are {len(videos_ready)}{'+' if len(videos_ready) > 5 else ''} videos ready:"
            n = 1
            for v in videos_ready:
                if not v['title']:
                    server = ctx.guild.id
                    category = discord.utils.get(ctx.guild.categories, name="reditor")
                    if not category:
                        message += f"\n{n}. *⚠️ Unknown video*"
                        continue
                    thumbnails = discord.utils.get(category.text_channels, name="thumbnails")
                    if not thumbnails:
                        message += f"\n{n}. *⚠️ Unknown video*"
                        continue
                    title = f"⚠️ [Unset video](https://discord.com/channels/{server}/{thumbnails.id}/{v['message']})"
                else:
                    title_escaped = v['title'].replace('*', '\\*')
                    title = f"**{title_escaped}**"

                message += f"\n{n}. {title}"
                n += 1
            if len(videos_ready) > 5:
                message += "\n..."

        if len(videos_exportable) == 0:
            message += "\n\nThere are no videos exportable! A random one will be picked."
        else:
            message += f"\n\nThere are **{len(videos_exportable)}** videos that can be exported."
        await ctx.send(embed=discord.Embed(
            title="Videos Ready",
            description=message,
            color=discord.colour.Colour.purple()
        ))

    @reditor.command()
    async def logging(self, ctx, level):
        positive = ["on", "y", "yes", "true", "t"]
        negative = ["off", "n", "no", "false", "f"]
        if level.lower() not in positive+negative:
            await ctx.send("Usage: `,reditor logging (on|off)`")
            return

        if level.lower() in positive:
            await pgsql.owner.set_config("rdt_debug", "True")
            await ctx.message.add_reaction("✅")
        else:
            await pgsql.owner.set_config("rdt_debug", "False")
            await ctx.message.add_reaction("✅")

    @reditor.command()
    async def characters(self, ctx):
        reditor_path = await pgsql.owner.get_config("rdt_reditor-server-path")
        if not reditor_path:
            await ctx.send("Please set the config variable `rdt_reditor-server-path` to the path of "
                           "the REditor server.")
            return

        await ctx.message.add_reaction("🕐")
        overview = self.get_character_overview(reditor_path + "data/logs/text-to-speech.csv")
        last_months = 5
        last_keys = list(overview.keys())[-last_months:]

        message = f"**Characters in the last {last_months} months:**"
        for k in last_keys:
            message += f"\n`{k:<7}`: `{overview[k]:>10,}`"
            if overview[k] > 4000000:
                message += " ⚠️"
        embed = discord.Embed(description=message, color=discord.colour.Colour.purple())
        await ctx.send(embed=embed)

    @staticmethod
    def get_character_overview(log_path):
        ret = {}
        fout = open(log_path, "r")
        reader = csv.reader(fout, delimiter=";")

        for timestamp, text, voice in reader:
            timestamp = float(timestamp)
            log_time = datetime.fromtimestamp(timestamp)
            key = f"{log_time.year}-{log_time.month}"
            if key not in ret:
                ret[key] = len(text)
            else:
                ret[key] += len(text)

        fout.close()
        return ret


def setup(bot):
    bot.add_cog(REditorCog(bot))
