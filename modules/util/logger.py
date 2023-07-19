import modules.data.reditor
import requests
from datetime import datetime, timedelta
import asyncio


last_log = datetime.now()


class Logger:
    @staticmethod
    async def log(event: "modules.util.log_events.LoggableEvent"):
        global last_log

        if not await modules.data.reditor.is_log_active(event.id):
            return

        if datetime.now() < last_log+timedelta(seconds=3):
            await asyncio.sleep(3)
        last_log = datetime.now()

        webhook_url = await modules.data.owner.get_config("rdt_logger")

        embed = {"embeds": [{
            "title": await event.name(),
            "color": event.severity,
            "description": event.get_log(),
            "footer": {"text": "sarto-helper-bot"}
        }]}
        requests.post(webhook_url, json=embed)
