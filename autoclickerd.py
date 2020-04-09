import time
import pyocr
import pyocr.builders
import os
import json

from PIL import Image, ImageEnhance

CACHE_DIR = os.path.join(os.getenv("HOME"), ".cache")
SCREEN_PNG = os.path.join(CACHE_DIR, "autoclickerd-screen.png")
SCREEN_JSON = os.path.join(CACHE_DIR, "autoclickerd-screen.json")

SCALE_IMAGEMAGICK = "400%"
SCALE_PIXELS = 4


class AutoClickerWordBoxBuilder(pyocr.builders.WordBoxBuilder):
    def __init__(self, tesseract_layout=1):
        tess_flags = ["--tessdata-dir", "/home/djwj/programming/autopy-test/tessdata", "--oem", "0", "--psm", str(tesseract_layout)]
        file_ext = ["html", "hocr"]
        tess_conf = ["hocr"]
        cun_args = ["-f", "hocr"]
        super(pyocr.builders.WordBoxBuilder, self).__init__(file_ext, tess_flags, tess_conf, cun_args)
        self.word_boxes = []
        self.tesseract_layout = tesseract_layout


if __name__ == "__main__":
    tools = pyocr.get_available_tools()
    tool = tools[0]

    langs = tool.get_available_languages()
    lang = langs[0]

    try:
        print("Updating cache of screen contents...")
        os.system("scrot -q 100 --overwrite " + SCREEN_PNG)

        screen = Image.open(SCREEN_PNG).convert('L')
        screen = ImageEnhance.Contrast(screen).enhance(1.5)
        screen.save(SCREEN_PNG + ".filtered.png")

        word_boxes = tool.image_to_string(
            screen,
            # lang=lang,
            # builder=pyocr.builders.WordBoxBuilder(),
        )
        word_to_box = {word_box.content.lower(): word_box.position for word_box in word_boxes}

        f = open(SCREEN_JSON, "w")
        json.dump(word_to_box, f)
        f.close()

        # time.sleep(3)

    except (KeyboardInterrupt, SystemExit):
        os.system("trash " + SCREEN_PNG)
        os.system("trash " + SCREEN_JSON)

    finally:
        quit()
