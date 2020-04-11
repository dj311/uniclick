title = """
                              _        __ _        __
               __  __ ____   (_)_____ / /(_)_____ / /__
              / / / // __ \ / // ___// // // ___// //_/
             / /_/ // / / // // /__ / // // /__ / ,<
             \__,_//_/ /_//_/ \___//_//_/ \___//_/|_|

"""
usage = """
usage: uniclick [--click | --double-click | --help]

uniclick allows you to click on any text using just your keyboard. when run, it will:
  1. take a screenshot of your desktop
  2. run optical character recognition (OCR) on it
  3. displays narrowing UI that allows you to select a word
  4. once your target word is selected, you cursor will be moved to its center.

if --click or --double-click are given, it will also click the left mouse button the
expected number of times.
"""
notes = """
uniclick expects to be inside an x11 session and requires a compositor running (tested
with compton).

system requirements:
  - tesseract
  - xdotool
  - scrot
  - python3

python requirements are in requirements.txt.

credits:
  - https://gist.github.com/initbrain/6628609 was vital for me getting the overlay
    window to work.
  - https://stackoverflow.com/questions/14200512#14269915 pointed me towards using
    the composite overlay window which made the ui reliable enough to actually be used.
  - tesseract, pyocr, xdotool, pillow, python-xlib, etc for doing the hard work..

"""
__doc__ = title + usage + notes

import daemon
import json
import os
import pyocr
import pyocr.builders
import sys
import time
import subprocess

from Xlib import X, XK, display
from PIL import Image, ImageEnhance
from daemon import pidfile

ALPHABET = "qwertyuiopasdfghjklzxcvbnm1234567890"

CACHE_DIR = os.path.join(os.getenv("HOME"), ".cache")
SCREEN_PNG = os.path.join(CACHE_DIR, "uniclick-screen.png")
DAEMON_PID = os.path.join(CACHE_DIR, "uniclick-daemon.pid")

tools = pyocr.get_available_tools()
tool = tools[0]

langs = tool.get_available_languages()
lang = langs[0]


def clean_word(word):
    return "".join(c for c in word.lower() if c in ALPHABET)

def get_screen():
    subprocess.run(["scrot", "-q", "100", "--overwrite", SCREEN_PNG])
    screen = Image.open(SCREEN_PNG).convert("L")
    screen = ImageEnhance.Contrast(screen).enhance(1.5)
    return screen


def ocr_screen(screen):
    word_boxes = tool.image_to_string(
        screen, lang=lang, builder=pyocr.builders.WordBoxBuilder(),
    )
    word_boxes = [(word_box.content, word_box.position) for word_box in word_boxes]

    return word_boxes


class Overlay:
    def __init__(self, display):
        self.display = display
        self.screen = self.display.screen()
        self.root = self.screen.root
        self.window = self.root.composite_get_overlay_window()._data["overlay_window"]

        self.root.grab_keyboard(
            1, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime,
        )

        colormap = self.screen.default_colormap
        self.color = colormap.alloc_color(0, 0, 0)
        self.xor_color = self.color.pixel ^ 0xFFFFFF

        self.gc = self.window.create_gc(
            foreground=self.xor_color,
            graphics_exposures=False,
            function=X.GXxor,
            subwindow_mode=X.IncludeInferiors,
        )

        self.window.change_attributes(event_mask=X.ExposureMask)
        self.display.sync()

    def draw_message(self, msg):
        win_geo = self.window.get_geometry()._data

        win_center_x = int(win_geo['x'] + win_geo['width']/2)
        win_center_y = int(win_geo['y'] + win_geo['height']/2)

        msg_width = len(msg)*6
        msg_height = 10

        msg_x = int(win_center_x - msg_width/2)
        msg_y = int(win_center_y - msg_height/2)

        border_x = 5
        border_y = 4

        self.window.fill_rectangle(
            self.gc,
            msg_x-border_x,
            msg_y-border_y,
            msg_width+2*border_x,
            msg_height+2*border_y,
        )
        self.window.draw_text(
            self.gc,
            msg_x,
            msg_y+msg_height,
            msg,
        )

    def draw(self, word_boxes, selection):
        if len(word_boxes) == 0:
            self.draw_message("uniclick: Search term produced no results. Press Backspace to remove characters or Escape to quit.")
            return

        index = 0
        for word, box in word_boxes:
            top_left, bottom_right = box

            x, y = top_left
            width, height = (
                abs(top_left[0] - bottom_right[0]),
                abs(top_left[1] - bottom_right[1]),
            )

            self.window.fill_rectangle(self.gc, x - 1, y - 1, width + 2, height + 2)

            if selection is not None and index == selection:
                self.window.rectangle(self.gc, x - 3, y - 3, width + 5, height + 5)

            index += 1


if __name__ == "__main__":
    num_args = len(sys.argv)

    if num_args == 2 and sys.argv[1] in ("help", "h", "--help", "-help", "-h"):
        print(title + usage)
        raise SystemExit

    if num_args == 2 and sys.argv[1] == "--click":
        clicks = 1
    elif num_args == 2 and sys.argv[1] == "--double-click":
        clicks = 2
    else:
        clicks = 0

    screen = get_screen()

    w = Overlay(display.Display())
    w.draw_message("uniclick: scanning screen...")
    w.display.sync()

    word_boxes = ocr_screen(screen)

    w.draw_message("uniclick: scanning screen...")  # undraw
    w.draw(word_boxes, None)
    w.display.sync()

    filtered_boxes = word_boxes.copy()
    selection = None
    search_term = ""
    found = False
    while not found:
        e = w.display.next_event()

        if e.type == X.KeyRelease:
            w.draw(filtered_boxes, selection)  # undraw current state

            keysym = w.display.keycode_to_keysym(e.detail, 0)
            string = XK.keysym_to_string(keysym)

            if keysym == XK.XK_BackSpace and len(search_term) >= 1:
                search_term = search_term[0:-1]

            elif keysym == XK.XK_Escape:
                raise SystemExit

            elif string is not None and string in ALPHABET:
                search_term += string

            elif selection is not None and keysym == XK.XK_Return:
                found = True

            elif keysym == XK.XK_Tab:
                if selection is not None:
                    selection += 1

            filtered_boxes = [
                (word, box) for word, box in word_boxes
                if clean_word(word).startswith(clean_word(search_term))
            ]

            num_boxes = len(filtered_boxes)
            num_unique_words = len({clean_word(word) for word, box in filtered_boxes})

            # enable <tab> selection once we have less than 5 results
            if selection is None and num_unique_words <= 5:
                selection = 0
            elif selection is not None and num_unique_words > 5:
                selection = None

            # wrap the selection pointer
            if selection is not None and selection >= num_boxes:
                selection = 0

            w.draw(filtered_boxes, selection)
            w.display.sync()

    w.window.unmap()
    w.display.sync()

    if len(filtered_boxes) < 1:
        print("couldn't find requested box")
        exit()

    word, box = filtered_boxes[selection]
    top_left, bottom_right = box

    center_x = (top_left[0] + bottom_right[0]) / 2
    center_y = (top_left[1] + bottom_right[1]) / 2
    center_x, center_y = int(center_x), int(center_y)

    subprocess.run(["xdotool", "mousemove", "--sync", str(center_x), str(center_y)])
    if clicks > 0:
        print(f"xdotool click --repeat {clicks} 1")
        subprocess.run(["xdotool", "click", "--repeat", str(clicks), "1"])
