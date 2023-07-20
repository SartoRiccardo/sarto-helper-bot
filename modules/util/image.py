from PIL import Image, ImageFont, ImageDraw, ImageOps
import os


BIN_PATH = os.path.abspath(os.path.dirname(__file__)) + "/../../bin"
FONT = ImageFont.truetype(BIN_PATH + "/thumbnail-font-bold.ttf", 100)
FONT_SHORTS = ImageFont.truetype(BIN_PATH + "/thumbnail-font-bold.ttf", 70)
WATERMARK_PATH = BIN_PATH + "/watermark.png"
WATERMARK_PATH_SHORTS = BIN_PATH + "/watermark-shorts.png"
ARROW_PATH = BIN_PATH + "/arrow.png"
CIRCLE_PATH = BIN_PATH + "/circle.png"

FONT_COLOR = (255, 255, 255)
STROKE_WIDTH = 8
STROKE_COLOR = (26, 35, 126)
THUMB_SIZE = (1280, 720)

BLACK = (0, 0, 0, 255)


def make_thumbnail(text: str,
                   image_path: str,
                   save_path: str,
                   max_chars_per_line: int = 20,
                   put_watermark: bool = False,
                   backdrop = None) -> None:
    base = Image.new("RGBA", THUMB_SIZE, color=backdrop if backdrop else BLACK)
    base_canvas = ImageDraw.Draw(base)

    text = split_text_in_lines(text, max_chars_per_line)

    background = Image.open(image_path).convert("RGBA")
    width, height = background.size
    if width/height > 16/9:
        bg_h = THUMB_SIZE[1]
        bg_w = int(bg_h*width/height)
        background = background.resize((bg_w, bg_h))
    elif width/height < 16/9:
        bg_w = THUMB_SIZE[0]
        bg_h = int(bg_w*height/width)
        background = background.resize((bg_w, bg_h))
    if backdrop:
        background.putalpha(int(255*0.7))

    bg_x = int((THUMB_SIZE[0]-bg_w)/2)
    bg_y = int((THUMB_SIZE[1]-bg_h)/2)
    base.alpha_composite(background, (bg_x, bg_y))

    base_canvas.multiline_text((int(THUMB_SIZE[0]/2), int(THUMB_SIZE[1]/2)),
                text.upper(), fill=FONT_COLOR, font=FONT, anchor="mm", align="center",
                stroke_fill=STROKE_COLOR, stroke_width=STROKE_WIDTH)
    if put_watermark:
        watermark = Image.open(WATERMARK_PATH)
        wm_w, wm_h = watermark.size
        base.paste(watermark, (0, THUMB_SIZE[1]-wm_h), watermark)
    base.save(save_path)
    base.close()

    reduce_size(save_path)


def add_circle(image_path, dest_path, r="4", x="c"):
    sizes = {
        "1": 250,  "2": 400,  "3": 520,  "4": 660,
        "sm": 250, "md": 400, "lg": 520, "xl": 660,
    }
    positions = {
        "l": (0, 30), "c": (310, 30), "r": (630, 30),
    }

    thumbnail = set_to_thumbnail_size(image_path)

    x_pos, y_pos = positions[x]
    size = sizes[r]
    x_pos += int((sizes["4"] - size)/2)
    y_pos += int((sizes["4"] - size)/2)
    circle = Image.open(CIRCLE_PATH).resize((size, size))

    thumbnail.paste(circle, (x_pos, y_pos), circle)

    thumbnail.save(dest_path)
    circle.close()
    thumbnail.close()
    reduce_size(dest_path)


def add_arrow(image_path, dest_path, x="c", y="c", size="md"):
    sizes = {"sm": (350, 350), "md": (480, 480), "lg": (640, 640)}
    # Format is (x, y, rotation). Coordinates for md size.
    positions = {
        "tl": (200, 150, 135), "tc": (400, 250, 90), "tr": (600, 150, 135),
        "cl": (300, 100, 180), "cc": (0,   100, 0),  "cr": (500, 100, 180),
        "bl": (200, 90, -135), "bc": (400, 400, 96), "br": (600, 90, -135),
    }

    thumbnail = set_to_thumbnail_size(image_path)
    arrow = Image.open(ARROW_PATH)

    x_pos, y_pos, rotation = positions[y+x]
    width, height = sizes[size]
    x_pos -= width - sizes["md"][0]
    y_pos -= height - sizes["md"][1]
    arrow = arrow.resize((width, height)).rotate(rotation)
    if x == "r":
        arrow = ImageOps.mirror(arrow)

    thumbnail.paste(arrow, (x_pos, y_pos), arrow)

    thumbnail.save(dest_path)
    arrow.close()
    thumbnail.close()
    reduce_size(dest_path)


def set_to_thumbnail_size(image_path):
    base = Image.new("RGBA", THUMB_SIZE)

    image = Image.open(image_path)
    w, h = image.size
    if w/h > 16/9:
        bg_h = THUMB_SIZE[1]
        bg_w = int(bg_h*w/h)
        image = image.resize((bg_w, bg_h))
    else:
        bg_w = THUMB_SIZE[0]
        bg_h = int(bg_w*h/w)
        image = image.resize((bg_w, bg_h))

    bg_x = int((THUMB_SIZE[0]-bg_w)/2)
    bg_y = int((THUMB_SIZE[1]-bg_h)/2)
    base.alpha_composite(image, (bg_x, bg_y))
    image.close()
    return base


def make_shorts_thumbnail(text, reaction, save_path):
    base = Image.open("bin/shorts-thmb-background.png")

    reaction_path = f"bin/reactions/{reaction}.png"
    if os.path.exists(reaction_path):
        reaction_img = Image.open(reaction_path)
        width, height = reaction_img.size
        new_height = int(THUMB_SIZE[1]*0.75)
        new_width = int(width * new_height/height)
        reaction_img = reaction_img.resize((new_width, new_height))
        base.paste(reaction_img, (THUMB_SIZE[0]-new_width, THUMB_SIZE[1]-new_height), reaction_img)

    text_canvas = ImageDraw.Draw(base)
    text = split_text_in_lines(text, 20)
    text_canvas.multiline_text((400, 200), text.upper(), fill=FONT_COLOR, font=FONT_SHORTS,
                               align="center", stroke_fill=STROKE_COLOR, stroke_width=STROKE_WIDTH,
                               anchor="mm")

    watermark = Image.open(WATERMARK_PATH_SHORTS)
    wm_w, wm_h = watermark.size
    base.paste(watermark, (0, THUMB_SIZE[1]-wm_h), watermark)

    base.save(save_path)


# YT thumbnails can't be > 2mb
def reduce_size(path):
    while os.stat(path).st_size > 2000000:
        thumb = Image.open(path)
        width, height = thumb.size
        thumb = thumb.resize((int(width*0.9), int(height*0.9)), Image.LANCZOS)
        thumb.save(path)
        thumb.close()


def split_text_in_lines(text, max_chars):
    words = text.split(" ")
    text_multi = ""
    for w in words:
        current_line = text_multi.split("\n")[-1]
        if len(current_line)+len(w)+1 > max_chars:
            text_multi += "\n"
        text_multi += " " + w
    return text_multi
