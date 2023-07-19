import discord
import modules.data.reditor
from typing import List, Dict, Any, Callable


EMOJIS = ["🪲", "ℹ️", "✅", "⚠️", "‼️"]


class ReditorLogSelect(discord.ui.Select):
    def __init__(self,
                 logs: List[Dict[Any, Any]],
                 callback: Callable = None):
        logs.sort(key=lambda l: (l["severity"], l["name"]))
        options = [
            discord.SelectOption(
                label=("❌ " if not log["active"] else "⏩ ") + log["name"],
                emoji=EMOJIS[log["severity"]],
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
                 timeout: float = 180):
        super().__init__(timeout=timeout)
        self.logs = logs
        self.select = ReditorLogSelect(logs, callback=self.select_log)
        self.add_item(self.select)
        self.active = True

    async def select_log(self, interaction: discord.Interaction, value: str) -> None:
        if not self.active:
            await interaction.response.send_message(
                content="This interaction timed out!",
                ephemeral=True
            )
            return

        log_id = value[:-1]
        is_active = bool(int(value[-1]))
        await modules.data.reditor.set_logging_status(log_id, not is_active)
        logs = await modules.data.reditor.get_logging_status()
        await interaction.response.send_message(
            content="Logging status changed! Select a log type to turn it off or on.",
            ephemeral=True,
            view=ReditorLog(logs)
        )
        self.active = False
