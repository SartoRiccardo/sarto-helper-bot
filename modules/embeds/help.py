import discord


class CogHelpEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="Using the \"cog\" command",
            description="Manages the bot's cogs. Owner only.",
            color=0xb103fc
        )
        self.add_field(name="list", value="Lists all loaded cogs", inline=True)
        self.add_field(name="load (name)", value="Loads a cog", inline=True)
        self.add_field(name="unload (name)", value="Unloads a cog", inline=True)
        self.add_field(name="reload (name)", value="Unloads and loads a cog simultaneously", inline=True)


class FeedsHelpEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="Using the \"feed\" command",
            description="Manages the feeds. Must have a `Feed Manager` role.",
            color=0xb103fc
        )
        self.add_field(name="list", value="Lists all the feeds you own", inline=True)
        self.add_field(name="new", value="Creates a new feed through a wizard", inline=True)
        self.add_field(name="delete", value="Deletes a feed you own", inline=True)
        self.add_field(name="edit", value="Edits a feed you own", inline=True)


class REditorHelpEmbed(discord.Embed):
    def __init__(self):
        super().__init__(
            title="Using the \"reditor\" command",
            description="Manages the REditor bot. Automatically searches threads and displays them.",
            color=0xb103fc
        )
        self.add_field(name="status", value="Checks if the REditor bot process is alive", inline=True)
        self.add_field(name="thumbnail (text)", value="Creates a thumbnail. Requires an image attachment.", inline=True)
        self.add_field(name="available", value="Shows which videos are exported and available for upload.", inline=True)
