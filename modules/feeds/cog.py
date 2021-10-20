import discord
import asyncio
from discord.ext import commands
import modules.data as psql
from modules.embeds.help import FeedsHelpEmbed
from modules.embeds.paginate import PaginationEmbed
from modules.embeds.success import NewFeedCreated
from modules.data.models import Feed
import math


class Feeds(commands.Cog):
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

    @commands.group()
    async def feed(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=FeedsHelpEmbed())

    @feed.command(aliases=["ls"])
    @commands.has_role("Feed Manager")
    async def list(self, ctx):
        feeds = await psql.feeds.get_feeds()
        feeds_per_page = 2
        pages = math.ceil(len(feeds)/feeds_per_page)
        current = 0

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
        embed = PaginationEmbed(ctx, title="Feeds List", description=description,
                                on_page_change=on_page_change, color=0xb103fc)
        embed.set_footer(text=f"{current+1}/{pages}")
        await embed.send()

    # I should be grouping the separate functions into... functions, but I'll do that later.
    @feed.command()
    @commands.has_role("Feed Manager")
    async def new(self, ctx):
        reactions = {
            "stop": "❌",
            "proceed": "✅",
            "skip": "➡️",
            "sfw": "🟢",
            "nsfw": "🔴",
            "sfw-nsfw": "🟠",
        }
        stop = False
        timeout = 60*2

        # Checker functions
        async def stop_operation(**kwargs):
            nonlocal stop
            if stop:
                return
            stop = True
            await embed.delete()
            if "timed_out" in kwargs and kwargs["timed_out"]:
                await ctx.send("Couldn't create new feed, you were inactive for too long. Be faster next time!")

        def check_message(e_message):
            return not stop and \
                e_message.author == ctx.message.author and \
                e_message.channel.id == embed.message.channel.id

        async def proceed_with_creation(**kwargs):
            nonlocal proceed
            proceed = True
            await embed.close()

        async def loop_back(**kwargs):
            nonlocal proceed
            proceed = False
            await embed.close()

        def set_rating(e_rating):
            async def inner(**kwargs):
                nonlocal rating
                rating = e_rating
                await embed.close()
            return inner

        # Name selection
        description = f"Create a new feed by following a few simple steps. " \
                      f"You can stop at any time by reacting with {reactions['stop']}.\n\n"
        description_create = f"Please write the name of the feed (e.g. `My Character's Feed`)."
        embed = PaginationEmbed(ctx, title="Create a Feed", description=description+description_create, color=0xb103fc,
                                timeout=timeout)
        embed.add_button(reactions["stop"], stop_operation)
        await embed.send()

        proceed = False
        while not proceed:
            try:
                message = await ctx.bot.wait_for("message", timeout=timeout, check=check_message)
                feed_name = message.content
                await embed.delete()
                if await psql.feeds.exists(feed_name):
                    description_err = f"There's already a feed with the name `{feed_name}`!\n\n"
                    embed.description = description_err + description_create
                    await embed.send()
                    continue

                proceed = True
            except asyncio.TimeoutError:
                await stop_operation(timed_out=True)

        if stop:
            return

        # Webhook
        description = f"Your feed will be named `{feed_name}`! Now please paste the URL to the webhook. " \
                      f"(It will be deleted immediately after for privacy reasons)."
        embed.description = description
        embed.title = "Assign a Webhook"
        await embed.send()

        proceed = False
        while not proceed:
            try:
                message = await ctx.bot.wait_for("message", timeout=timeout, check=check_message)
                webhook_url = message.content
                await message.delete()
                await embed.delete()
                if not webhook_url.startswith("https://discord.com/api/webhooks/"):
                    embed.description = "That's not an URL to a Discord Webhook! Please paste one.\n\n" \
                                        "Discord Webhooks look like this: " \
                                        "`https://discord.com/api/webhooks/<numbers>/<random>`"
                    await embed.send()
                    continue
                proceed = True
            except asyncio.TimeoutError:
                await stop_operation(timed_out=True)

        if stop:
            return

        # Tags
        description = f"Please type the tags for your feed. They will be separated by commas.\n\n" \
                      f"A few examples: `alice margatroid` `alice margatroid,blush,grin`"
        embed.title = "Select Tags"

        proceed = False
        while not proceed:
            try:
                embed.remove_button(reactions["proceed"])
                embed.add_button(reactions["stop"], stop_operation)
                embed.description = description
                await embed.send()
                message = await ctx.bot.wait_for("message", timeout=timeout, check=check_message)
                tags = message.content.split(",")
                tags = [t.strip().replace(" ", "_") for t in tags if len(t) > 0]
                if len(tags) == 0:
                    continue

                await embed.delete()
                tags_list = [f"`{t}`" for t in tags]
                embed.description = f"The tags you want are: {', '.join(tags_list)}"
                embed.add_button(reactions["proceed"], proceed_with_creation)
                embed.add_button(reactions["stop"], loop_back)
                await embed.send(synchronous=True)
                await embed.delete()
            except asyncio.TimeoutError:
                await stop_operation(timed_out=True)

        if stop:
            return

        # Blacklist
        description = f"Please type the __blacklisted__ tags for your feed. They will be separated by commas. " \
                      f"If an entry has any of these tags, it will not be shown " \
                      f"(The bot also has a global blacklist).\n\n" \
                      f"A few examples: `loli` `loli,shota,guro`\n" \
                      f"__You can also write `skip` to skip this step.__"
        embed.title = "Select Blacklisted Tags"

        proceed = False
        blacklist = []
        while not proceed:
            try:
                embed.remove_button(reactions["proceed"])
                embed.add_button(reactions["stop"], stop_operation)
                embed.description = description
                await embed.send()
                message = await ctx.bot.wait_for("message", timeout=timeout, check=check_message)
                if message.content.lower() == "skip":
                    await embed.delete()
                    break

                blacklist = message.content.split(",")
                blacklist = [t.strip().replace(" ", "_") for t in blacklist if len(t) > 0]
                if len(blacklist) == 0:
                    break

                await embed.delete()
                blacklist_list = [f"`{t}`" for t in blacklist]
                embed.description = f"The tags you want to blacklist are: {', '.join(blacklist_list)}"
                embed.add_button(reactions["proceed"], proceed_with_creation)
                embed.add_button(reactions["stop"], loop_back)
                await embed.send(synchronous=True)
                await embed.delete()
            except asyncio.TimeoutError:
                await stop_operation(timed_out=True)

        if stop:
            return

        # Rating
        description = f"Last step! Select the rating of the feed:\n" \
                      f"{reactions['sfw']} - SFW Feed\n" \
                      f"{reactions['nsfw']} - NSFW Feed\n" \
                      f"{reactions['sfw-nsfw']} - Both SFW and NSFW"
        embed.title = "Select Feed Rating"
        embed.description = description
        embed.remove_button(reactions["proceed"])
        embed.remove_button(reactions["stop"])
        embed.add_button(reactions['sfw'], set_rating(Feed.SFW))
        embed.add_button(reactions['nsfw'], set_rating(Feed.NSFW))
        embed.add_button(reactions['sfw-nsfw'], set_rating(Feed.BOTH))

        proceed = False
        rating = Feed.SFW
        while not proceed:
            try:
                await embed.send(synchronous=True)
                await embed.delete()
                proceed = True
            except asyncio.TimeoutError:
                await stop_operation(timed_out=True)

        if stop:
            return

        # End
        new_feed = Feed(name=feed_name, webhook=webhook_url, tags=tags,
                        blacklist=blacklist, rating=rating)
        await psql.feeds.add_feed(new_feed)
        await ctx.send(embed=NewFeedCreated(new_feed))

    @feed.command(aliases=["delete", "remove"])
    @commands.has_role("Feed Manager")
    async def _delete(self, ctx):
        pass

    @feed.command()
    @commands.has_role("Feed Manager")
    async def edit(self, ctx):
        pass


def setup(bot):
    bot.add_cog(Feeds(bot))
