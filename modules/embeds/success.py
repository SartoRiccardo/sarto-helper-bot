import discord
import modules.data.models.Feed


class NewFeedCreated(discord.Embed):
    def __init__(self, feed):
        super().__init__(
            title=feed.name,
            description="You can change this feed by using the command "
                        f"`,feed change {feed.name}`",
            color=feed.color
        )
        self.add_field(name="Tags", value=", ".join([f"`{tag}`" for tag in feed.tags]), inline=True)
        if len(feed.blacklist) > 0:
            self.add_field(name="Blacklist", value=", ".join([f"`{tag}`" for tag in feed.blacklist]), inline=True)

        rating_descriptions = {
            modules.data.models.Feed.SFW: "🟢 SFW",
            modules.data.models.Feed.NSFW: "🔴 NSFW",
            modules.data.models.Feed.BOTH: "🟠 Both SFW and NSFW",
        }
        self.add_field(name="Rating", value=rating_descriptions[feed.rating], inline=True)
