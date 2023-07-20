import csv
import traceback
import random
import os
import re
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
import modules.util.log_events
import modules.views.ReditorLog
from typing import Optional, Literal, Tuple
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

    reditor = discord.app_commands.Group(name="reditor",
                                         description="Commands for REditor management.")

    @reditor.command(name="status", description="Check if the server is online!")
    @modules.util.discordutils.owner_only()
    async def status(self, interaction: discord.Interaction):
        out = subprocess.check_output('ps -aux | grep reditor-srv.py', shell=True)
        is_running = len(out.decode().split("\n")) == 4
        await interaction.response.send_message(
            content=f"The process is{'' if is_running else ' not'} running!",
            ephemeral=True,
        )

    @reditor.command(name="setup", description="Create a brand new REditor category")
    @modules.util.discordutils.owner_only()
    async def setup(self, interaction: discord.Interaction):
        """
        Create the category "reditor";
        Create the channels "#log", "#threads", "#cdn", and "#thumbnails";
        Create the webhook "REditor Logger".
        """
        category = await interaction.guild.create_category("reditor")

        log_channel = await category.create_text_channel("log")
        webhook = await log_channel.create_webhook(name="REditor Logger")

        channels = ["threads", "thumbnails", "cdn"]
        await asyncio.wait(
            [category.create_text_channel(c) for c in channels] +
            [pgsql.owner.set_config("rdt_logger", webhook.url)],
            return_when=asyncio.ALL_COMPLETED
        )

        await interaction.response.send_message(
            content=f"All done! {SUCCESS_REACTION}",
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await asyncio.gather(*[
            self.check_thread_confirmation(payload),
            self.check_video_deletion(payload),
        ])

    async def check_video_deletion(self, payload: discord.RawReactionActionEvent) -> None:
        """
        Listen for video deletion. Happens when reacting with ❌ to a "React with a thumbnail and title to x" message.
        Fired by on_raw_reaction_add
        """
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

    async def check_thread_confirmation(self, payload: discord.RawReactionActionEvent) -> None:
        """
        Listen for thread confirmation.
        Fired by on_raw_reaction_add
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
        cdn_channel = discord.utils.get(category.text_channels, name="cdn")
        if not (thumbnail_channel and thread_channel and cdn_channel) or thread_channel.id != payload.channel_id:
            return

        message = await thread_channel.fetch_message(payload.message_id)
        if not message:
            return

        chosen_threads = []
        for i in range(len(message.reactions)):
            r = message.reactions[i]
            if r.count > 1:
                chosen_threads.append(i)
        await message.delete()

        threads = await pgsql.reditor.get_threads(payload.message_id, filter=chosen_threads)
        messages = []
        tokens_used = modules.util.chatgpt.PrompTokens()
        for t in threads:
            embed = discord.Embed(description="Something went wrong loading this!")
            try:
                embed, tokens = await REditorCog.make_embed(t["title"], cdn_channel)
            except Exception as exc:
                await modules.util.logger.Logger.log(
                    modules.util.log_events.LogError(traceback.format_exc()[:1900])
                )
            tokens_used += tokens
            messages.append(
                await thumbnail_channel.send(
                    f"Reply with a title and a thumbnail for **{t['title']}**",
                    embed=embed,
                )
            )
        await pgsql.reditor.choose_threads(
            [(threads[i]["id"], messages[i].id) for i in range(len(threads))]
        )
        await modules.util.logger.Logger.log(modules.util.log_events.LogTokensUsedGPT(
            tokens_used.prompt, tokens_used.completion
        ))

    @staticmethod
    async def make_embed(thread_title: str,
                         cdn_channel: discord.TextChannel) -> Tuple[discord.Embed, modules.util.chatgpt.PrompTokens]:
        tokens_used = modules.util.chatgpt.PrompTokens()
        titles, tokens = await modules.util.chatgpt.get_video_titles(thread_title)
        tokens_used += tokens
        titles_str = "\n".join([f"{i}. {titles[i]}" for i in range(len(titles))])

        w_text, tokens = await modules.util.chatgpt.get_highlighted_text(thread_title)
        tokens_used += tokens
        w_text = re.sub(r"\[(.+?)]", lambda m: f"__{m.group(1)}__", w_text)

        image_hint, tokens = await modules.util.chatgpt.get_image_idea(thread_title)
        tokens_used += tokens
        thumb_str = f"- **Image Hint:** {image_hint if image_hint else 'N/A'}\n" \
                    f"- **Weighted Text**: {w_text}"
        thumbnail = None
        if image_hint:
            thumbnail, tokens = await REditorCog.get_thumbnail(image_hint, w_text, cdn_channel)
            tokens_used += tokens

        embed = discord.Embed(
            title=titles[0],
            colour=8847874,
        )
        if thumbnail:
            embed.set_image(url=thumbnail)
        embed.add_field(name="Thread", value=f"- **Title**: {thread_title}", inline=True)
        embed.add_field(name="Thumbnail", value=thumb_str, inline=True)
        embed.add_field(name="Titles", value=titles_str, inline=False)
        return embed, tokens_used

    @staticmethod
    async def get_thumbnail(image_hint: str,
                            text: str,
                            cdn_channel: discord.TextChannel) -> Tuple[str or None, modules.util.chatgpt.PrompTokens]:
        queries, tokens = await modules.util.chatgpt.get_pixabay_prompts(image_hint)
        images = []
        for q in queries:
            images = (await modules.util.req.pixabay_search(q))[:10]
            if len(images) > 0:
                break
        if len(images) == 0:
            return None, tokens

        path_ids = []
        for img in images:
            r = random.randint(1, 1000000)
            await modules.util.req.download_file(img, f"tmp/pixabay-{r}.png")
            modules.util.image.make_thumbnail(text, f"tmp/pixabay-{r}.png", f"tmp/thumbnail-{r}.png")
            path_ids.append(r)
        message = await cdn_channel.send(
            image_hint,
            files=[discord.File(fp=f"tmp/thumbnail-{r}.png") for r in path_ids]
        )
        thumbnail = message.attachments[0].url
        for r in path_ids:
            os.remove(f"tmp/pixabay-{r}.png")
            os.remove(f"tmp/thumbnail-{r}.png")
        return thumbnail, tokens

    def is_thumbnail_channel(self, guild_id: int, channel_id: int) -> bool:
        guild = discord.utils.get(self.bot.guilds, id=guild_id)
        category = discord.utils.get(guild.categories, name="reditor")
        if not category:
            return False
        channel = discord.utils.get(category.text_channels, name="thumbnails")
        return channel and channel.id == channel_id

    @commands.Cog.listener()
    async def on_message(self, message):
        await asyncio.gather(*[
            self.check_add_video_meta(message),
            self.check_scene_reaction_add(message),
        ])

    async def check_add_video_meta(self, message: discord.Message) -> None:
        """
        Check if a message is adding metadata to a video (title/thumbnail).
        Fired by on_message
        """
        if (len(message.attachments) == 0 and "https://" not in message.content) or \
                message.reference is None or \
                not self.is_thumbnail_channel(message.reference.guild_id, message.reference.channel_id):
            return

        if "https://" in message.content:
            img_start_idx = message.content.index("https://")
            thumbnail = message.content[img_start_idx:]
            message.content = message.content[:img_start_idx].strip()
        else:
            thumbnail = message.attachments[0].url

        reply_id = message.reference.message_id
        title = message.content
        is_short = "\N{SHORTS}" in title
        title = title.replace("\N{SHORTS}", "")

        await pgsql.reditor.set_video_meta(reply_id, title, thumbnail, is_short=is_short)

        reference = message.reference.cached_message
        if not reference:
            reference = await message.channel.fetch_message(reply_id)
        if reference and reference.author.id == self.bot.user.id and not reference.edited_at:
            await reference.edit(
                content=reference.content[:39] + reference.content[41:-2],
                embed=None
            )
        await message.add_reaction("✅")

    async def check_scene_reaction_add(self, message: discord.Message) -> None:
        """
        Check if a message is adding a commend/reaction to a scene.
        Fired by on_message.
        """
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

    @reditor.command(name="available", description="Shows the videos available to export")
    @discord.app_commands.rename(type_str="video_type")
    @discord.app_commands.describe(type_str="The video type to show")
    async def available(self,
                        interaction: discord.Interaction,
                        type_str: Optional[Literal["short", "video"]] = "video"):
        videos_ready = await pgsql.reditor.get_uploadable(shorts=(type_str == "short"))
        videos_exportable = await pgsql.reditor.get_exportable(shorts=(type_str == "short"))

        embed = discord.Embed(
            color=self.bot.default_embed_color
        )

        if len(videos_ready) == 0:
            embed.add_field(
                name="Exported",
                value=f"There are no {type_str}s ready!",
            )
        else:
            message = f"There are **{len(videos_ready)}{'+' if len(videos_ready) > 5 else ''}** {type_str}s ready:"
            message += self.get_video_list_message(interaction, videos_ready, type_str)
            embed.add_field(
                name="Exported",
                value=message,
            )

        if len(videos_exportable) == 0:
            embed.add_field(
                name="Created",
                value=f"There are no {type_str}s exportable!",
            )
        else:
            message = f"There are **{len(videos_exportable)}** {type_str}s that can be exported."
            message += self.get_video_list_message(interaction, videos_exportable, type_str)
            embed.add_field(
                name="Created",
                value=message,
            )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    @staticmethod
    def get_video_list_message(interaction: discord.Interaction,
                               video_list,
                               type_str: Optional[Literal["short", "video"]] = "video") -> str:
        message = ""
        n = 1
        for v in video_list:
            if not v['title']:
                server = interaction.guild.id
                category = discord.utils.get(interaction.guild.categories, name="reditor")
                if not category:
                    message += f"\n{n}. *⚠️ Unknown {type_str}*"
                    continue
                thumbnails = discord.utils.get(category.text_channels, name="thumbnails")
                if not thumbnails:
                    message += f"\n{n}. *⚠️ Unknown {type_str}*"
                    continue
                title = f"⚠️ [Unset video](https://discord.com/channels/{server}/{thumbnails.id}/{v['message']})"
            else:
                title_escaped = v['title'].replace('*', '\\*')
                title = f"{title_escaped}"

            message += f"\n{n}. {title}"
            n += 1
            if n > 4:
                break

        if len(video_list) > 4:
            message += "\n5. ..."

        return message

    @reditor.command(name="log", description="Set the logging status for REditor events")
    @modules.util.discordutils.owner_only()
    async def logging(self, interaction: discord.Interaction):
        logs = await pgsql.reditor.get_logging_status()
        view = modules.views.ReditorLog.ReditorLog(logs, interaction)
        await interaction.response.send_message(
            content="Select a log type to turn it off or on.",
            ephemeral=True,
            view=view
        )

    @reditor.command(name="charcount", description="See how many characters have been used up.")
    async def characters(self, interaction: discord.Interaction):
        reditor_path = await pgsql.owner.get_config("rdt_reditor-server-path")
        if not reditor_path:
            await interaction.response.send_message("Please set the config variable `rdt_reditor-server-path` to the "
                                                    "path of the REditor server.")
            return

        await interaction.response.defer()
        overview = self.get_character_overview(reditor_path + "data/logs/text-to-speech.csv")
        last_months = 5
        last_keys = list(overview.keys())[-last_months:]

        months = {"1": "Jan", "2": "Feb", "3": "Mar", "4":  "Apr", "5":  "May", "6":  "Jun",
                  "7": "Lug", "8": "Aug", "9": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
        message_pts = []
        for k in last_keys:
            part = f"- `{months[k[5:]]} {k[:4]}`: `{overview[k]:>9,}`"
            if overview[k] > 1_000_000:
                part += " ⚠️"
            message_pts.append(part)
        message = "None!" if len(message_pts) == 0 else "\n".join(message_pts)
        embed = discord.Embed(title=f"TTS Characters usage (last {len(last_keys)} months)",
                              description=message,
                              color=self.bot.default_embed_color)
        await interaction.edit_original_response(embed=embed)

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
