from discord import app_commands, Interaction, Guild, CategoryChannel


def owner_only():
    async def check(interaction: Interaction):
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(check)


def get_reditor_category(guild: Guild) -> CategoryChannel or None:
    category = None
    for c in guild.categories:
        if "reditor" in c.name.lower():
            category = c
            break
    return category
