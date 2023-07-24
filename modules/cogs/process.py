import discord
import re
import subprocess
import modules.data.connection
from datetime import datetime, timedelta
from discord.ext import commands, tasks


class ProcessCog(commands.Cog):
    process = discord.app_commands.Group(name="process",
                                         description="Commands for process tracking.")
    CHECK_EVERY = 10*60

    def __init__(self, bot):
        self.bot = bot
        now = int((datetime.now() + timedelta(seconds=self.CHECK_EVERY)).timestamp())
        self.next_check_processes = datetime.fromtimestamp(now - now % self.CHECK_EVERY)

    @process.command(name="add", description="Track a command")
    @discord.app_commands.describe(process_id="The name of the process",
                                   process_name="A human readable name of the process")
    async def cmd_add(self, interaction: discord.Interaction, process_id: str, process_name: str) -> None:
        await modules.data.owner.track_process(process_id, process_name)
        await interaction.response.send_message(
            content=f"✅ **All Done!** The process {process_name} will be tracked!",
            ephemeral=True,
        )

    @process.command(name="remove", description="Stop tracking a command")
    @discord.app_commands.describe(process_name="The process' human readable name.")
    async def cmd_remove(self, interaction: discord.Interaction, process_name: str) -> None:
        await modules.data.owner.untrack_process(process_name)
        await interaction.response.send_message(
            content=f"✅ **All Done!** The process {process_name} is no longer tracked!",
            ephemeral=True,
        )

    @process.command(name="channel", description="Set a channel as a Process Overview channel.")
    @discord.app_commands.describe(channel="The channel to start posting on.")
    async def cmd_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        await modules.data.owner.set_config("process-ch", channel.id)
        await interaction.response.send_message(
            content=f"✅ **All Done!** The channel {channel.mention} will be regularly updated!",
            ephemeral=True,
        )

    @tasks.loop(seconds=10)
    async def task_check_processes(self, ctx):
        now = datetime.now()
        if now < self.next_check_processes:
            return
        self.next_check_processes += timedelta(seconds=self.CHECK_EVERY)

        processes = sorted(await modules.data.owner.get_processes(), key=lambda x: x["pname"])
        pids: dict[str, int] = {}

        out = subprocess.check_output("ps -aux", shell=True).decode()
        for ln in out.split("\n"):
            for process in processes:
                if process["pid"] in ln:
                    match = re.match(r"\S+\s+(\d+)", ln)
                    pids[process["pid"]] = int(match.group(1))

        template = "【{}】  `{:>8}`   {}"
        content = "# Bot Overview\n" \
                  " __**Status**__           __**PID**__         __**Process**__"
        content_parts = []
        for process in processes:
            content_parts.append(template.format(
                "🟢" if process in pids.keys() else "🔴",
                pids[process["pid"]] if process in pids.keys() else "",
                process["pname"],
            ))
        content += "\n".join(content_parts)
        content += f"*Last updated: <t:{int(now.timestamp())}:R>*"

        channel_id = int(await modules.data.owner.get_config("process-ch"))
        if channel_id is None:
            return
        channel: discord.TextChannel = await self.get_channel(channel_id)
        if channel is None:
            return
        async for msg in channel.history(limit=25):
            if msg.author == self.bot:
                await msg.edit(content=content)
                return
        await channel.send(content=content)

    async def get_channel(self, ch_id: int) -> discord.TextChannel or None:
        ch = self.bot.get_channel(ch_id)
        if ch is not None:
            return ch
        try:
            ch = self.bot.fetch_channel(ch_id)
            return ch
        except discord.NotFound:
            return None

async def setup(bot):
    await bot.add_cog(ProcessCog(bot))
