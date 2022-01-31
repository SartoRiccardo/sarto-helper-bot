import modules.data.owner
import aiohttp
from datetime import datetime, timedelta
import time


last_log = datetime.now()


class Logger:
    DEBUG = 14938877
    INFO = 2001125
    SUCCESS = 4431943
    ERROR = 12986408
    WARN = 16772696

    @staticmethod
    async def log(message, severity):
        global last_log
        if datetime.now() < last_log+timedelta(seconds=3):
            time.sleep(3)
        last_log = datetime.now()

        title = "Info"
        if severity == Logger.DEBUG:
            title = "Debug"
        elif severity == Logger.SUCCESS:
            title = "Success"
        elif severity == Logger.ERROR:
            title = "Error"
        elif severity == Logger.WARN:
            title = "Warning"

        webhook_url, debug = await modules.data.owner.get_config(["rdt_logger", "rdt_debug"])
        if webhook_url is None or \
                not (debug == "True") and severity == Logger.DEBUG:
            return
        embed = {"embeds": [{
            "title": title,
            "color": severity,
            "description": message,
            "footer": {"text": "sarto-helper-bot"}
        }]}
        
        with aiohttp.ClientSession() as session:
            session.post(webhook_url, json=embed)
