from PIL import Image, ImageFont, ImageDraw
import os


BIN_PATH = os.path.abspath(os.path.dirname(__file__)) + "/../../bin"
FONT = ImageFont.truetype(BIN_PATH + "/thumbnail-font-bold.ttf", 100)
WATERMARK_PATH = BIN_PATH + "/watermark.png"
FONT_COLOR = (255, 255, 255)
STROKE_WIDTH = 8
STROKE_COLOR = (26, 35, 126)
THUMB_SIZE = (1280, 720)

BLACK = (0, 0, 0, 255)


def make_thumbnail(text, image_path, save_path, max_chars_per_line=20):
    base = Image.new("RGBA", THUMB_SIZE, color=BLACK)
    base_canvas = ImageDraw.Draw(base)

    words = text.split(" ")
    text_multi = ""
    for w in words:
        current_line = text_multi.split("\n")[-1]
        if len(current_line)+len(w)+1 > max_chars_per_line:
            text_multi += "\n"
        text_multi += " " + w
    text = text_multi

    watermark = Image.open(WATERMARK_PATH)
    wm_w, wm_h = watermark.size

    background = Image.open(image_path)
    width, height = background.size
    if width/height > 16/9:
        bg_h = THUMB_SIZE[1]
        bg_w = int(bg_h*width/height)
        background = background.resize((bg_w, bg_h))
    else:
        bg_w = THUMB_SIZE[0]
        bg_h = int(bg_w*height/width)
        background = background.resize((bg_w, bg_h))
    background.putalpha(int(255*0.7))

    bg_x = int((THUMB_SIZE[0]-bg_w)/2)
    bg_y = int((THUMB_SIZE[1]-bg_h)/2)
    base.alpha_composite(background, (bg_x, bg_y))

    base_canvas.multiline_text((int(THUMB_SIZE[0]/2), int(THUMB_SIZE[1]/2)),
                text.upper(), fill=FONT_COLOR, font=FONT, anchor="mm", align="center",
                stroke_fill=STROKE_COLOR, stroke_width=STROKE_WIDTH)
    base.paste(watermark, (0, THUMB_SIZE[1]-wm_h), watermark)
    base.save(save_path)
    base.close()

    # YT thumbnails can't be > 2mb
    while os.stat(save_path).st_size > 2000000:
        thumb = Image.open(save_path)
        width, height = thumb.size
        thumb = thumb.resize((int(width*0.9), int(height*0.9)), Image.ANTIALIAS)
        thumb.save(save_path)
        thumb.close()
