title = """

                     _        __ _        __
      __  __ ____   (_)_____ / /(_)_____ / /__
     / / / // __ \ / // ___// // // ___// //_/
    / /_/ // / / // // /__ / // // /__ / ,<
    \__,_//_/ /_//_/ \___//_//_/ \___//_/|_|

"""
usage = """
commands:
         update :: take and ocr a screenshot, save results to the cache. the
                   `list` and `goto` commands need an up-to-date cache to be
                   useful.
           list :: output a list of all words on screen.
    goto <word> :: move the mouse to <word> on screen.
           help :: sohw this message.

"""
__doc__ = title + usage

import json
import os
import pyocr
import pyocr.builders
import sys
import time

from PIL import Image, ImageEnhance

CACHE_DIR = os.path.join(os.getenv("HOME"), ".cache")
SCREEN_PNG = os.path.join(CACHE_DIR, "uniclick-screen.png")
SCREEN_JSON = os.path.join(CACHE_DIR, "uniclick-screen.json")

tools = pyocr.get_available_tools()
tool = tools[0]

langs = tool.get_available_languages()
lang = langs[0]

def ocr_screen():
    os.system("scrot -q 100 --overwrite " + SCREEN_PNG)

    screen = Image.open(SCREEN_PNG).convert('L')
    screen = ImageEnhance.Contrast(screen).enhance(1.5)
    screen.save(SCREEN_PNG + ".filtered.png")

    word_boxes = tool.image_to_string(
        screen,
        lang=lang,
        builder=pyocr.builders.WordBoxBuilder(),
    )
    word_to_box = {word_box.content: word_box.position for word_box in word_boxes}

    return word_to_box


if __name__=="__main__":
    command, *args = sys.argv[1:]

    if command == 'update':
        word_to_box = ocr_screen()

        f = open(SCREEN_JSON, "w")
        json.dump(word_to_box, f)
        f.close()

        quit(0)

    elif command == 'list':
        f = open(SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

        for word, box in word_to_box.items():
            print(word)

        quit(0)

    elif command == "goto":
        f = open(SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

        [word] = args
        box = word_to_box.get(word)
        if box is None:
            print("couldn't find requested box")

        top_left, bottom_right = box

        center_x = (top_left[0] + bottom_right[0])/2
        center_y = (top_left[1] + bottom_right[1])/2

        print("going to", center_x, center_y)

        os.system("xdotool mousemove --sync " + str(int(center_x)) + " " + str(int(center_y)))

    elif command in ("help", "-h", "h", "--help", "-help"):
        print(title + usage)
