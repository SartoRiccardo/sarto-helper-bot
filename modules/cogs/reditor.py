import csv
import random
import os
import discord
import asyncio
import importlib
import subprocess
from datetime import datetime
from discord.ext import commands
import modules.data
import modules.data.owner
import modules.data.reditor
import modules.util
from modules.embeds.help import REditorHelpEmbed
pgsql = modules.data
util = modules.util


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class REditorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_checked = None

    def cog_unload(self):
        importlib.reload(modules.data.reditor)
        importlib.reload(modules.data.owner)
        importlib.reload(modules.util.logger)
        importlib.reload(modules.util.image)
        importlib.reload(util)
        importlib.reload(pgsql)

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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await asyncio.gather(*[
            self.check_thread_confirmation(payload),
            self.check_video_deletion(payload),
        ])

    async def check_video_deletion(self, payload):
        if str(payload.emoji) != "❌":
            return

        guild = discord.utils.get(self.bot.guilds, id=payload.guild_id)
        if guild.owner_id != payload.user_id:
            return

        category = discord.utils.get(guild.categories, name="reditor")
        if not category:
            return

        thumbnail_channel = discord.utils.get(category.text_channels, name="thumbnails")
        if not thumbnail_channel or thumbnail_channel.id != payload.channel_id:
            return

        await pgsql.reditor.discard_video(message_id=payload.message_id)

    async def check_thread_confirmation(self, payload):
        """
        Listen for thread confirmation
        :return: bool: Whether the
        """
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

        message = await thread_channel.fetch_message(payload.message_id)
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
        await asyncio.gather(*[
            self.check_add_video_meta(message),
            self.check_scene_reaction_add(message),
        ])

    async def check_add_video_meta(self, message):
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
            reference = await message.channel.fetch_message(reply_id)
        if reference and reference.author.id == self.bot.user.id and not reference.edited_at:
            await reference.edit(content=reference.content[:39] + reference.content[41:-2])
        await message.add_reaction("✅")

    async def check_scene_reaction_add(self, message):
        if message.reference is None:
            return
        scene_data = await pgsql.reditor.get_scene_info(message.channel.id, message.reference.message_id)
        if scene_data is None:
            return
        document_id, scene_id = scene_data

        reactions = {
            "\U0001f604": "joy",
            "\U0001f914": "think",
            "\U0001f621": "angry",
            "\U0001f60f": "smug",
            "\U0001F937": "shrug",
        }
        for rctn in reactions.keys():
            await message.add_reaction(rctn)

        try:
            def check(payload: discord.RawReactionActionEvent):
                return payload.message_id == message.id and \
                    str(payload.emoji) in reactions.keys() and \
                    payload.user_id == message.author.id

            emoji_payload = await self.bot.wait_for("raw_reaction_add", timeout=10, check=check)
            choice_emoji = str(emoji_payload.emoji)
        except asyncio.TimeoutError:
            choice_emoji = random.choice(list(reactions.keys()))

        await message.clear_reactions()
        await message.add_reaction(choice_emoji)
        reaction = reactions[choice_emoji]

        await self.add_reaction_to_scene(document_id, scene_id, reaction, message.content)

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

    @staticmethod
    async def add_reaction_to_scene(document_id, scene_id, reaction, text):
        """
        TEMPORARY METHOD. Will be overridden by an API call to the REditor server.
        """
        reditor_saves_path = await pgsql.owner.get_config("rdt_saves-path")
        script_path = os.path.join(reditor_saves_path, f"{document_id:05d}", "scenes", f"{scene_id:05d}", "script.txt")
        if not os.path.exists(script_path):
            return False

        file = open(script_path)
        parts = []
        while True:
            parts.append("".join([file.readline() for _ in range(4)]))
            if file.readline() == "":
                break
        file.close()

        parts[-1] += "\n"
        if "[reaction=" in parts[-1]:
            parts.pop(-1)
        parts.append(f"[reaction={reaction}]\n{text}\nmale-1-neural\n0.75")

        script_new = "\n".join(parts)
        file = open(script_path, "w")
        file.write(script_new)
        file.close()

        return True


async def setup(bot):
    await bot.add_cog(REditorCog(bot))
