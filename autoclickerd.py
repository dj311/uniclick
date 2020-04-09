import time
import pyocr
import pyocr.builders
import os
import json

from PIL import Image, ImageEnhance

CACHE_DIR = os.path.join(os.getenv("HOME"), ".cache")
SCREEN_PNG = os.path.join(CACHE_DIR, "autoclickerd-screen.png")
SCREEN_JSON = os.path.join(CACHE_DIR, "autoclickerd-screen.json")

if __name__ == "__main__":
    tools = pyocr.get_available_tools()
    tool = tools[0]

    langs = tool.get_available_languages()
    lang = langs[0]

    try:
        while True:
            print("Updating cache of screen contents...")
            os.system("scrot -q 100 --overwrite " + SCREEN_PNG)

            screen = Image.open(SCREEN_PNG).convert('L')
            screen = ImageEnhance.Contrast(screen).enhance(1.5)
            screen.save(SCREEN_PNG + ".filtered.png")

            word_boxes = tool.image_to_string(
                screen,
                lang=lang,
                builder=pyocr.builders.WordBoxBuilder(),
            )
            word_to_box = {word_box.content.lower(): word_box.position for word_box in word_boxes}

            f = open(SCREEN_JSON, "w")
            json.dump(word_to_box, f)
            f.close()

            time.sleep(3)

    except (KeyboardInterrupt, SystemExit):
        pass

    finally:
        os.system("trash " + SCREEN_PNG)
        os.system("trash " + SCREEN_JSON)
        quit()
