import discord
import re
import subprocess
import importlib
import asyncio
from discord.ext import commands
import modules.data
import modules.data.feeds
from modules.embeds.help import FeedsHelpEmbed
from modules.embeds.InteractiveEmbed import InteractiveEmbed
from modules.embeds.success import FeedOverview
from modules.data.models import Feed
import math
psql = modules.data


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class FeedCog(commands.Cog):
    REACTIONS = {
        "stop": "❌",
        "proceed": "✅",
        "skip": "➡️",
        "sfw": "🟢",
        "nsfw": "🔴",
        "sfw-nsfw": "🟠",
    }

    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        importlib.reload(modules.data.owner)

    @commands.group(aliases=["feeds"], invoke_without_command=True)
    async def feed(self, ctx, *args):
        if ctx.invoked_subcommand is None and len(args) == 0:
            await ctx.send(embed=FeedsHelpEmbed())
            return

        feed_name = " ".join(args)
        feed = await psql.feeds.get_feed(feed_name, ignore_case=True)
        await ctx.send(embed=FeedOverview(feed))

    @feed.command()
    @commands.is_owner()
    async def status(self, ctx):
        out = subprocess.check_output('ps -aux | grep discordbooru', shell=True)
        if len(out.decode().split("\n")) == 4:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")

    @feed.command(aliases=["ls"])
    @commands.has_role("Feed Manager")
    async def list(self, ctx):
        feeds = await psql.feeds.get_feeds()
        feeds_per_page = 15
        pages = math.ceil(len(feeds)/feeds_per_page)
        current = 0

        if pages == 0:
            await ctx.send("No feeds!")
            return

        async def on_page_change(change=0, caller=None, **kwargs):
            nonlocal current
            last_current = current
            current += change
            if current < 0:
                current = 0
            if current > pages-1:
                current = pages-1

            if last_current == current:
                return
            start_i = feeds_per_page*current
            description = "\n".join(["• "+f.name for f in feeds[start_i:start_i+feeds_per_page]])
            caller.description = description
            caller.set_footer(text=f"{current+1}/{pages}")
            await caller.update()

        description = "\n".join(["• "+f.name for f in feeds[:feeds_per_page]])
        embed = InteractiveEmbed(ctx, title="FeedCog List", description=description,
                                 on_page_change=on_page_change, color=0xb103fc)
        embed.set_footer(text=f"{current+1}/{pages}")
        await embed.send()

    @feed.command()
    @commands.has_role("Feed Manager")
    async def new(self, ctx):
        stop = False
        timeout = 60*2

        async def stop_operation(**kwargs):
            nonlocal stop
            if stop:
                return
            stop = True
            await embed.delete()
            if "timed_out" in kwargs and kwargs["timed_out"]:
                await ctx.send("Couldn't create new feed, you were inactive for too long. Be faster next time!")

        fields = {
            "name": FeedCog.select_feed_name,
            "webhook": FeedCog.select_feed_webhook,
            "tags": FeedCog.select_feed_tags,
            "rating": FeedCog.select_feed_rating
        }
        new_feed = Feed(empty=True)
        embed = InteractiveEmbed(ctx, timeout=timeout)

        for key in fields:
            func = fields[key]
            value = await func(ctx, embed, timeout, on_stop=stop_operation, feed=new_feed)
            if stop or value is None:
                return
            new_feed.set_value(key, value)

        await psql.feeds.add_feed(new_feed)
        await ctx.send(embed=FeedOverview(new_feed))

    @feed.command(aliases=["delete", "remove"])
    @commands.has_role("Feed Manager")
    async def _delete(self, ctx, *name):
        name = " ".join(name)
        feed = await psql.feeds.get_feed(name)
        if feed is None:
            await ctx.message.add_reaction("❓")
            return

        async def cancel(**kwargs):
            await embed.close()

        async def delete_feed(**kwargs):
            await psql.feeds.delete_feed(name)
            await ctx.message.add_reaction(FeedCog.REACTIONS["success"])

        embed = InteractiveEmbed(ctx, title=f"Delete {name}?", color=int(feed.color, 16))
        embed.add_button(FeedCog.REACTIONS["stop"], cancel)
        embed.add_button(FeedCog.REACTIONS["proceed"], delete_feed)
        await embed.send(synchronous=True)
        await embed.delete()

    @feed.command(aliases=["edit"])
    @commands.has_role("Feed Manager")
    async def change(self, ctx, *name):
        name = " ".join(name)
        feed = await psql.feeds.get_feed(name)
        if feed is None:
            await ctx.message.add_reaction("❓")
            return

        buttons = {
            "1️⃣": {"field": "name", "function": FeedCog.select_feed_name,
                    "description": "Feed Name"},
            "2️⃣": {"field": "webhook", "function": FeedCog.select_feed_webhook,
                    "description": "Feed Webhook"},
            "3️⃣": {"field": "tags", "function": FeedCog.select_feed_tags,
                    "description": "Feed Tags"},
            "4️⃣": {"field": "blacklist", "function": FeedCog.select_feed_blacklist,
                    "description": "Feed Blacklist"},
            "5️⃣": {"field": "rating", "function": FeedCog.select_feed_rating,
                    "description": "Feed Rating"},
            "6️⃣": {"field": "color", "function": FeedCog.select_feed_color,
                    "description": "Feed Color"},
        }
        timeout = 60 * 2

        def callback_wrapper(button_config):
            async def inner(**kwargs):
                async def abort_changes(**kwargs):
                    await embed.delete()

                await menu_embed.delete()
                value = await button_config["function"](ctx, embed, timeout, feed=feed,
                                                        on_stop=abort_changes)
                if value is None:
                    return

                feed.set_value(button_config["field"], value)
                await psql.feeds.edit_feed(name, feed)
                await ctx.message.add_reaction(SUCCESS_REACTION)
            return inner

        async def close(**kwargs):
            await menu_embed.delete()

        menu_embed = await InteractiveEmbed.from_dict(FeedOverview(feed).to_dict(), ctx)
        menu_embed.description = "React with the field you want to change:\n"
        button_list = [f"{key}  {buttons[key]['description']}" for key in buttons]
        menu_embed.description += "\n".join(button_list)
        menu_embed.add_button(FeedCog.REACTIONS["stop"], close)
        for btn in buttons:
            menu_embed.add_button(btn, callback_wrapper(buttons[btn]))

        embed = InteractiveEmbed(ctx, timeout=timeout, color=int(feed.color, 16))
        await menu_embed.send(synchronous=True)

    @staticmethod
    async def select_feed_name(ctx, embed, timeout, on_stop=None, feed=None, **kwargs):
        if feed is None:
            description = f"Create a new feed by following a few simple steps. " \
                          f"You can stop at any time by reacting with {FeedCog.REACTIONS['stop']}.\n\n"
            description_create = f"Please write the name of the feed (e.g. `My Character's Feed`)."
            embed.title = "Create a Feed"
        else:
            description = ""
            description_create = f"Please write the name of the feed (e.g. `My Character's Feed`)."
            embed.title = "Change your feed's name"

        embed.description = description + description_create
        embed.color = 0xb103fc
        if on_stop:
            embed.add_button(FeedCog.REACTIONS['stop'], on_stop)
        await embed.send()

        while True:
            try:
                message = await ctx.bot.wait_for("message", timeout=timeout, check=FeedCog.check_message(ctx, embed))
                feed_name = message.content
                if embed.closed:
                    return
                await embed.delete()
                if await psql.feeds.exists(feed_name):
                    description_err = f"There's already a feed with the name `{feed_name}`!\n\n"
                    embed.description = description_err + description_create
                    await embed.send()
                    continue

                return feed_name
            except asyncio.TimeoutError:
                if on_stop:
                    await on_stop(timed_out=True)
                return None

    @staticmethod
    async def select_feed_webhook(ctx, embed, timeout, on_stop=None, feed=None, **kwargs):
        embed.description = f"Please paste the URL to the webhook. " \
                            f"(It will be deleted immediately after for privacy reasons)."
        embed.title = f"Assign a Webhook to {'your feed' if feed is None else feed.name}"
        await embed.send()

        while True:
            try:
                message = await ctx.bot.wait_for("message", timeout=timeout, check=FeedCog.check_message(ctx, embed))
                webhook_url = message.content
                if embed.closed:
                    return
                await embed.delete()
                if not webhook_url.startswith("https://discord.com/api/webhooks/"):
                    embed.description = "That's not an URL to a Discord Webhook! Please paste one.\n\n" \
                                        "Discord Webhooks look like this: " \
                                        "`https://discord.com/api/webhooks/<numbers>/<random>`"
                    await embed.send()
                    continue
                await message.delete()
                return webhook_url
            except asyncio.TimeoutError:
                if on_stop:
                    await on_stop(timed_out=True)

    @staticmethod
    async def select_feed_tags(ctx, embed, timeout, on_stop=None, **kwargs):
        description = f"Please type the tags for your feed. They will be separated by commas.\n\n" \
                      f"A few examples: `alice margatroid` `alice margatroid,blush,grin`"
        embed.title = "Select Tags"

        async def confirm(**kwargs):
            nonlocal confirmed
            confirmed = True
            await embed.close()

        async def retry(**kwargs):
            await embed.close()

        while True:
            try:
                embed.remove_button(FeedCog.REACTIONS["proceed"])
                if on_stop:
                    embed.add_button(FeedCog.REACTIONS["stop"], on_stop)
                embed.description = description
                await embed.send()
                message = await ctx.bot.wait_for("message", timeout=timeout, check=FeedCog.check_message(ctx, embed))
                if embed.closed:
                    return
                tags = message.content.lower().split(",")
                tags = [t.strip().replace(" ", "_") for t in tags if len(t) > 0]
                if len(tags) == 0:
                    continue
                await embed.delete()
                tags_list = [f"`{t}`" for t in tags]

                confirmed = False
                embed.description = f"The tags you want are: {', '.join(tags_list)}"
                embed.add_button(FeedCog.REACTIONS["proceed"], confirm)
                embed.add_button(FeedCog.REACTIONS["stop"], retry)
                await embed.send(synchronous=True)
                await embed.delete()

                if confirmed:
                    return tags
            except asyncio.TimeoutError:
                if on_stop:
                    await on_stop(timed_out=True)

    @staticmethod
    async def select_feed_rating(ctx, embed, timeout, on_stop=None, **kwargs):
        description = f"Last step! Select the rating of the feed:\n" \
                      f"{FeedCog.REACTIONS['sfw']} - SFW Feed\n" \
                      f"{FeedCog.REACTIONS['nsfw']} - NSFW Feed\n" \
                      f"{FeedCog.REACTIONS['sfw-nsfw']} - Both SFW and NSFW"
        embed.title = "Select Feed Rating"
        embed.description = description
        embed.remove_button(FeedCog.REACTIONS["proceed"])
        embed.remove_button(FeedCog.REACTIONS["stop"])

        def set_rating(e_rating):
            async def inner(**kwargs):
                nonlocal rating
                rating = e_rating
                await embed.close()
            return inner

        rating = Feed.SFW
        embed.add_button(FeedCog.REACTIONS['sfw'], set_rating(Feed.SFW))
        embed.add_button(FeedCog.REACTIONS['nsfw'], set_rating(Feed.NSFW))
        embed.add_button(FeedCog.REACTIONS['sfw-nsfw'], set_rating(Feed.BOTH))

        try:
            await embed.send(synchronous=True)
            await embed.delete()
            return rating
        except asyncio.TimeoutError:
            if on_stop:
                await on_stop(timed_out=True)

    @staticmethod
    async def select_feed_blacklist(ctx, embed, timeout, on_stop=None, feed=None, **kwargs):
        embed.description = f"Please type the __blacklisted__ tags for your feed. " \
                            f"Any artwork containing any of these will be discarded. You can " \
                            f"separate them with commas.\n\n" \
                            f"A few examples: `loli` `loli,shota`"
        embed.title = "Select Blacklisted Tags"

        confirm_embed = InteractiveEmbed(ctx, color=int(feed.color, 16))
        confirm_description = "Do you want to blacklist these tags? `{}`"

        async def confirm(**kwargs):
            nonlocal confirmed
            confirmed = True
            await confirm_embed.close()

        async def retry(**kwargs):
            await confirm_embed.close()

        confirm_embed.add_button(FeedCog.REACTIONS["proceed"], confirm)
        confirm_embed.add_button(FeedCog.REACTIONS["stop"], retry)

        while True:
            try:
                if on_stop:
                    embed.add_button(FeedCog.REACTIONS["stop"], on_stop)
                await embed.send()
                message = await ctx.bot.wait_for("message", timeout=timeout, check=FeedCog.check_message(ctx, embed))
                if embed.closed:
                    return
                blacklist = message.content.lower()
                blacklist = [tag.strip().replace(" ", "_") for tag in blacklist.split(",")
                             if len(tag.strip().replace(" ", "_")) > 0]
                if len(blacklist) == 0:
                    continue

                await embed.delete()

                confirmed = False
                confirm_embed.description = confirm_description.format("`, `".join(blacklist))
                await confirm_embed.send(synchronous=True)
                await confirm_embed.delete()

                if confirmed:
                    return blacklist
            except asyncio.TimeoutError:
                if on_stop:
                    await on_stop(timed_out=True)

    @staticmethod
    async def select_feed_color(ctx, embed, timeout, on_stop=None, **kwargs):
        embed.description = f"Select the color of your feed in HEX.\n\n" \
                            f"A few examples: `ff00ff` `#9b603f`"
        description_err = "__Invalid color! It must be a hexadecimal value!__\n"
        embed.title = "Select Feed Color"

        confirm_embed = InteractiveEmbed(ctx)
        confirm_embed.description = "⬅️\n" \
                                    "⬅️\n" \
                                    "⬅️ Is this\n" \
                                    "⬅️ color ok?\n" \
                                    "⬅️\n" \
                                    "⬅️"

        async def confirm(**kwargs):
            nonlocal confirmed
            confirmed = True
            await confirm_embed.close()

        async def retry(**kwargs):
            await confirm_embed.close()

        confirm_embed.add_button(FeedCog.REACTIONS["proceed"], confirm)
        confirm_embed.add_button(FeedCog.REACTIONS["stop"], retry)

        color_re = r"^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        while True:
            try:
                if on_stop:
                    embed.add_button(FeedCog.REACTIONS["stop"], on_stop)
                await embed.send()
                message = await ctx.bot.wait_for("message", timeout=timeout, check=FeedCog.check_message(ctx, embed))
                if embed.closed:
                    return
                color = message.content.lower()

                await embed.delete()
                if not re.search(color_re, color):
                    embed.description = description_err + embed.description
                    continue
                if color.startswith("#"):
                    color = color[1:]

                confirmed = False
                confirm_embed.color = int(color, 16)
                await confirm_embed.send(synchronous=True)
                await confirm_embed.delete()

                if confirmed:
                    return color
                embed.description = embed.description.replace(description_err, "")
            except asyncio.TimeoutError:
                if on_stop:
                    await on_stop(timed_out=True)

    @staticmethod
    def check_message(ctx, embed):
        def inner(e_message):
            return e_message.author == author and \
                   e_message.channel.id == channel_id

        channel_id = embed.message.channel.id
        author = ctx.message.author
        return inner


async def setup(bot):
    await bot.add_cog(FeedCog(bot))
