import os
import re
import discord
import importlib
from random import randint
from discord.ext import commands
import modules.data
import modules.data.owner
import modules.data.reditor
import modules.util
pgsql = modules.data
util = modules.util


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class ThumbnailCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        importlib.reload(modules.data.reditor)
        importlib.reload(modules.data.owner)
        importlib.reload(modules.util.logger)
        importlib.reload(modules.util.image)
        importlib.reload(util)
        importlib.reload(pgsql)

    @staticmethod
    async def fetch_thumb_image_url(ctx):
        if len(ctx.message.attachments) == 0:
            # Fallback if no image attached
            if not ctx.message.reference:
                # Use last image sent in the channel by a non-bot user
                thumb_img_url = None
                history = [msg async for msg in ctx.channel.history(limit=100)]
                for message in history:
                    if not message.author.bot and len(message.attachments) > 0:
                        return message.attachments[0].url

                if not thumb_img_url:
                    await ctx.send("You must attach an image!")
                    return

            # If replying to a message, use that message's image, if any.
            reference = ctx.message.reference
            if reference.cached_message:
                message = reference.cached_message
            else:
                message = await ctx.channel.fetch_message(reference.message_id)
                if not message:
                    await ctx.send("Are you replying to a message that's too old? Please send the image again!")
                    return
            return message.attachments[0].url
        return ctx.message.attachments[0].url

    @commands.group(aliases=["thmb"], invoke_without_command=True)
    async def thumbnail(self, ctx, *, thumb_text):
        if ctx.invoked_subcommand is not None:
            return

        thumb_img_url = await self.fetch_thumb_image_url(ctx)
        if thumb_img_url is None:
            return

        if not (thumb_img_url.endswith(".png") or thumb_img_url.endswith(".jpg")):
            await ctx.send("You must attach an image!")
            return

        backdrop = util.image.BLACK
        if "-b" in thumb_text:
            thumb_text = thumb_text.replace("-b", "")
            backdrop = None

        watermark = False
        if "-w" in thumb_text:
            thumb_text = thumb_text.replace("-w", "")
            watermark = True

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.requests.download_file(thumb_img_url, source_path)
        util.image.make_thumbnail(thumb_text, source_path, dest_path, backdrop=backdrop,
                                  put_watermark=watermark)
        await self.send_and_rm(source_path, dest_path, ctx)

    @thumbnail.command()
    async def circle(self, ctx, *args):
        thumb_img_url = await self.fetch_thumb_image_url(ctx)
        if thumb_img_url is None:
            return

        if not (thumb_img_url.endswith(".png") or thumb_img_url.endswith(".jpg")):
            await ctx.send("You must attach an image!")
            return

        circle_config = {
            "r": "4",
            "x": "c",
        }
        allowed_values = {
            "r": [str(n+1) for n in range(4)] + ["sm", "md", "lg", "xl"],
            "x": ["l", "c", "r"],
        }

        regex = r"(.+)(?:=|:|-)(.+)"
        for arg in args:
            arg = arg.lower()

            match = re.search(regex, arg)
            if match is None:
                for key in allowed_values:
                    if arg in allowed_values[key]:
                        circle_config[key] = arg
                        break
                continue

            key = match.group(1)
            val = match.group(2)
            if key in circle_config and val in allowed_values[key]:
                circle_config[key] = val

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.requests.download_file(thumb_img_url, source_path)
        util.image.add_circle(source_path, dest_path, **circle_config)
        await self.send_and_rm(source_path, dest_path, ctx)

    @thumbnail.command()
    async def arrow(self, ctx, arg0="cc", arg1="md"):
        thumb_img_url = await self.fetch_thumb_image_url(ctx)
        if thumb_img_url is None:
            return

        if not (thumb_img_url.endswith(".png") or thumb_img_url.endswith(".jpg")):
            await ctx.send("You must attach an image!")
            return

        arrow_config = {
            "x": "c",
            "y": "c",
            "size": "md"
        }
        allowed_values = {
            "x": ["l", "c", "r"],
            "y": ["t", "c", "b"],
            "size": ["sm", "md", "lg"],
        }

        if arg1 in allowed_values["size"]:
            arrow_config["size"] = arg1

        if arg0 in allowed_values["size"]:
            arrow_config["size"] = arg0
        else:
            for char in arg0:
                if char in allowed_values["x"] and char != "c":
                    arrow_config["x"] = char
                elif char in allowed_values["y"] and char != "c":
                    arrow_config["y"] = char

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.requests.download_file(thumb_img_url, source_path)
        util.image.add_arrow(source_path, dest_path, **arrow_config)
        await self.send_and_rm(source_path, dest_path, ctx)

    @staticmethod
    async def send_and_rm(source_path, dest_path, ctx):
        fp = open(dest_path, "rb")
        await ctx.send(file=discord.File(fp, filename="thumbnail.png"))
        fp.close()
        if os.path.exists(source_path):
            os.remove(source_path)
        if os.path.exists(dest_path):
            os.remove(dest_path)


async def setup(bot):
    await bot.add_cog(ThumbnailCog(bot))
