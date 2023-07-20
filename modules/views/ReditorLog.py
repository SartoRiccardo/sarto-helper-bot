import discord
import modules.data.reditor
from typing import List, Dict, Any, Callable


EMOJIS = ["🪲", "💬", "✅", "⚠️", "🆘"]


class ReditorLogSelect(discord.ui.Select):
    def __init__(self,
                 logs: List[Dict[Any, Any]],
                 callback: Callable = None):
        logs.sort(key=lambda l: (l["severity"], l["name"]))
        options = [
            discord.SelectOption(
                label=EMOJIS[log["severity"]] + " " + log["name"],
                emoji=("🟢" if log["active"] else "🔴"),
                description=log["description"],
                value=log["log_id"] + str(1 if log["active"] else 0)
            )
            for log in logs
        ]
        self.callback_func = callback
        super().__init__(
            placeholder="Select a log type",
            options=options
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.callback_func:
            await self.callback_func(interaction, self.values[0])


class ReditorLog(discord.ui.View):
    def __init__(self,
                 logs: List[Dict[Any, Any]],
                 original_interaction: discord.Interaction,
                 timeout: float = 180):
        super().__init__(timeout=timeout)
        self.logs = logs
        self.select = ReditorLogSelect(logs, callback=self.select_log)
        self.add_item(self.select)
        self.original_interaction = original_interaction

    async def select_log(self, interaction: discord.Interaction, value: str) -> None:
        log_id = value[:-1]
        is_active = bool(int(value[-1]))
        await modules.data.reditor.set_logging_status(log_id, not is_active)
        logs = await modules.data.reditor.get_logging_status()

        await interaction.response.send_message(
            content=f"**✅ All set!**\n`{log_id}` has been turned {'off' if is_active else 'on'}",
            ephemeral=True,
        )
        await self.original_interaction.edit_original_response(
            content="Select a log type to turn it off or on.",
            view=ReditorLog(logs, self.original_interaction)
        )
