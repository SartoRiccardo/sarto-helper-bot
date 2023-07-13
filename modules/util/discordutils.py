from discord import app_commands, Interaction


def owner_only():
    async def check(interaction: Interaction):
        return await interaction.client.is_owner(interaction.user)
    return app_commands.check(check)
