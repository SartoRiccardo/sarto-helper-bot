import os
import discord
import importlib
from random import randint
from discord.ext import commands
import modules.data
import modules.data.owner
import modules.data.reditor
import modules.util
from typing import Optional, Literal
pgsql = modules.data
util = modules.util


SUCCESS_REACTION = '\N{THUMBS UP SIGN}'


class ThumbnailCog(commands.Cog):
    thumbnail = discord.app_commands.Group(name="thumbnail", description="Various commands to create thumbnails.")

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
    async def fetch_thumb_image_url(interaction: discord.Interaction) -> str or None:
        # Use last image sent in the channel by a non-bot user
        history = [msg async for msg in interaction.channel.history(limit=100)]
        for message in history:
            if not message.author.bot and len(message.attachments) > 0:
                return message.attachments[0].url
        return None

    @thumbnail.command(name="create", description="Turn the latest image sent into a thumbnail")
    @discord.app_commands.rename(thumb_text="text")
    @discord.app_commands.describe(thumb_text="The thumbnail text.",
                                   with_backdrop="If the thumbnail will have a black backdrop behind the text.",
                                   watermark="Add a watermark to the thumbnail.",
                                   image_url="The URL of the image to use as a source.")
    async def create(self,
                     interaction: discord.Interaction,
                     thumb_text: str,
                     with_backdrop: Optional[bool] = True,
                     watermark: Optional[bool] = False,
                     image_url: Optional[str] = None):
        if image_url is None:
            thumb_img_url = await self.fetch_thumb_image_url(interaction)
            if thumb_img_url is None:
                return
        else:
            thumb_img_url = image_url

        await interaction.response.send_message(
            content="Working on it...",
            ephemeral=True
        )
        backdrop = util.image.BLACK if with_backdrop else None

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.req.download_file(thumb_img_url, source_path)
        util.image.make_thumbnail(thumb_text, source_path, dest_path, backdrop=backdrop,
                                  put_watermark=watermark)
        await self.send_and_rm(source_path, dest_path, interaction)

    @thumbnail.command(name="circle", description="Add a circle in a thumbnail.")
    @discord.app_commands.describe(position="The circle's position",
                                   size="The circle's radius",
                                   image_url="The URL of the image to use as a source.")
    async def circle(self,
                     interaction: discord.Interaction,
                     position: Optional[Literal["left", "center", "right"]] = "center",
                     size: Optional[Literal["1", "2", "3", "4"]] = "4",
                     image_url: Optional[str] = None):
        if image_url is None:
            thumb_img_url = await self.fetch_thumb_image_url(interaction)
            if thumb_img_url is None:
                return
        else:
            thumb_img_url = image_url
        
        await interaction.response.send_message(
            content="Working on it...",
            ephemeral=True
        )

        circle_config = {
            "r": size,
            "x": position[0],
        }
        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.req.download_file(thumb_img_url, source_path)
        util.image.add_circle(source_path, dest_path, **circle_config)
        await self.send_and_rm(source_path, dest_path, interaction)

    @thumbnail.command(name="arrow", description="Add an arrow to a thumbnail.")
    @discord.app_commands.describe(position_x="The arrow's horizontal pointing position",
                                   position_y="The arrow's vertical pointing position",
                                   size="The arrow's size",
                                   image_url="The URL of the image to use as a source.")
    async def arrow(self,
                    interaction: discord.Interaction,
                    position_x: Optional[Literal["left", "center", "right"]] = "center",
                    position_y: Optional[Literal["top", "center", "bottom"]] = "center",
                    size: Optional[Literal["small", "medium", "large"]] = "medium",
                    image_url: Optional[str] = None):
        if image_url is None:
            thumb_img_url = await self.fetch_thumb_image_url(interaction)
            if thumb_img_url is None:
                return
        else:
            thumb_img_url = image_url

        await interaction.response.send_message(
            content="Working on it...",
            ephemeral=True
        )

        allowed_values_transform = {
            "small": "sm", "medium": "md", "large": "lg",
        }
        arrow_config = {
            "x": position_x[0],
            "y": position_y[0],
            "size": allowed_values_transform[size],
        }

        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        source_path = f"{tmp_path}/thumbnail-{rand_id}-src.png"
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"

        await util.req.download_file(thumb_img_url, source_path)
        util.image.add_arrow(source_path, dest_path, **arrow_config)
        await self.send_and_rm(source_path, dest_path, interaction)

    @thumbnail.command(name="short", description="A thumbnail for a short")
    @discord.app_commands.describe(text="The text for the thumbnail.",
                                   reaction="Doremy's reaction.")
    async def short(self,
                    interaction: discord.Interaction,
                    text: str,
                    reaction: Optional[Literal["joy", "angry", "shrug", "smug", "think"]] = "joy"):
        await interaction.response.send_message(
            content="Working on it...",
            ephemeral=True
        )
        tmp_path = os.path.abspath(os.path.dirname(__file__)) + "/../../tmp"
        if not os.path.exists(tmp_path):
            os.mkdir(tmp_path)

        rand_id = randint(0, 1000000)
        dest_path = f"{tmp_path}/thumbnail-{rand_id}.png"
        util.image.make_shorts_thumbnail(text, reaction, dest_path)
        await self.send_and_rm("", dest_path, interaction)

    @staticmethod
    async def send_and_rm(source_path: str, dest_path: str, interaction: discord.Interaction):
        fp = open(dest_path, "rb")
        await interaction.channel.send(
            file=discord.File(fp, filename="thumbnail.png")
        )
        fp.close()
        if os.path.exists(source_path):
            os.remove(source_path)
        if os.path.exists(dest_path):
            os.remove(dest_path)


async def setup(bot):
    await bot.add_cog(ThumbnailCog(bot))
