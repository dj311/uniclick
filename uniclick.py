title = """
                              _        __ _        __
               __  __ ____   (_)_____ / /(_)_____ / /__
              / / / // __ \ / // ___// // // ___// //_/
             / /_/ // / / // // /__ / // // /__ / ,<
             \__,_//_/ /_//_/ \___//_//_/ \___//_/|_|

"""
usage = """
usage: uniclick (update | ui | help) [args]

commands:
  update :: screenshot then ocr the screen, saving results to the cache. adding
            `--daemon` will run this repeatedly in the background, once every 3
            seconds.

      ui :: list and goto word via an overlay ui. results are narrowed by typing letters
            (case insensitive and only considers 'qwertyuiopasdfghjklzxcvbnm1234567890').
              - <tab> cycles between results when you have 5 or less.  unfortunately the
                cycling order is a little stochastic.
              - <backspace> untypes letters (as you'd expect).
              - <enter> completes the search. the default action is to move the
                mouse. adding --click or --double-click will do click the left mouse
                button the expected number of times after moving.

    help :: show this message.

system requirements:
  - tesseract
  - xdotool
  - scrot
  - python3

it expects to be inside an x11 session with a compositor running (tested with compton).

python requirements are in requirements.txt.

example setups for i3:
  1. scan then use overlay ui for picking
        bindsym $mod+c exec uniclick update \\
            | zenity --progress --auto-close --auto-kill --pulsate \\
                     --text "uniclick loading..." \\
            && uniclick ui

  2. start a daemon which scans the screen every 3 seconds
        bindsym $mod+c exec uniclick update --daemon && uniclick ui

there are tradeoffs between these options:
  - running the update as a daemon means that it's be responsive, but you'll waste a lot
    compute and there's a high likelihood of the cached data being out of date.
  - running the update on demand shouldn't ever give out of date results, but will be
    slow (approx 5 secs on my machine).

credits:
  - https://gist.github.com/initbrain/6628609 was vital for me getting the overlay
    window to work.
  - https://stackoverflow.com/questions/14200512#14269915 pointed me towards using
    the composite overlay window which made the ui reliable enough to actually be used.
  - tesseract, pyocr, xdotool, pillow, python-xlib, etc for doing the hard work..

"""
__doc__ = title + usage

import daemon
import json
import os
import pyocr
import pyocr.builders
import sys
import time

from Xlib import X, XK, display
from PIL import Image, ImageEnhance
from daemon import pidfile

ALPHABET = "qwertyuiopasdfghjklzxcvbnm1234567890"

CACHE_DIR = os.path.join(os.getenv("HOME"), ".cache")
SCREEN_PNG = os.path.join(CACHE_DIR, "uniclick-screen.png")
SCREEN_JSON = os.path.join(CACHE_DIR, "uniclick-screen.json")
DAEMON_PID = os.path.join(CACHE_DIR, "uniclick-daemon.pid")

tools = pyocr.get_available_tools()
tool = tools[0]

langs = tool.get_available_languages()
lang = langs[0]


def clean_word(word):
    return "".join(c for c in word.lower() if c in ALPHABET)


def ocr_screen():
    os.system(f"scrot -q 100 --overwrite {SCREEN_PNG}.new.png")

    old_screen = Image.open(SCREEN_PNG).convert("L")
    new_screen = Image.open(SCREEN_PNG + ".new.png").convert("L")
    screen_changed = old_screen.tobytes() != new_screen.tobytes()

    if screen_changed:
        os.system(f"mv {SCREEN_PNG}.new.png {SCREEN_PNG}")
        screen = ImageEnhance.Contrast(new_screen).enhance(1.5)

        word_boxes = tool.image_to_string(
            screen, lang=lang, builder=pyocr.builders.WordBoxBuilder(),
        )
        word_to_box = {word_box.content: word_box.position for word_box in word_boxes}

    else:
        print("screen hasn't changed")
        f = open(SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

    return word_to_box


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

    def draw(self, word_boxes, selection):
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
    if len(sys.argv) <= 1:
        command, *args = "help", []
    else:
        command, *args = sys.argv[1:]

    if command == "update" and args == ["--daemon"]:
        with daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(DAEMON_PID)):
            while True:
                word_to_box = ocr_screen()

                f = open(SCREEN_JSON, "w")
                json.dump(word_to_box, f)
                f.close()

                time.sleep(3)

    elif command == "update" and args == []:
        word_to_box = ocr_screen()

        f = open(SCREEN_JSON, "w")
        json.dump(word_to_box, f)
        f.close()

        quit(0)

    elif command == "ui":
        if len(args) > 0 and args[0] == "--click":
            clicks = 1
        elif len(args) > 0 and args[0] == "--double-click":
            clicks = 2
        else:
            clicks = 0

        f = open(SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

        w = Overlay(display.Display())
        w.draw(word_to_box.items(), None)
        w.display.sync()

        filtered_boxes = word_to_box.copy()
        selection = None
        search_term = ""
        found = False
        while not found:
            e = w.display.next_event()

            if e.type == X.KeyRelease:
                w.draw(filtered_boxes.items(), selection)  # undraw current state

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

                filtered_boxes = {
                    word: box
                    for word, box in word_to_box.items()
                    if clean_word(word).startswith(clean_word(search_term))
                }

                num_boxes = len(filtered_boxes)

                # enable <tab> selection once we have less than 5 results
                if selection is None and num_boxes <= 5:
                    selection = 0
                elif selection is not None and num_boxes > 5:
                    selection = None

                # wrap the selection pointer
                if selection is not None and selection >= num_boxes:
                    selection = 0

                w.draw(filtered_boxes.items(), selection)
                w.display.sync()

        w.window.unmap()
        w.display.sync()

        matches = list(filtered_boxes.values())
        if len(matches) < 1:
            print("couldn't find requested box")
            exit()

        match = matches[selection]
        top_left, bottom_right = match

        center_x = (top_left[0] + bottom_right[0]) / 2
        center_y = (top_left[1] + bottom_right[1]) / 2
        center_x, center_y = int(center_x), int(center_y)

        os.system(f"xdotool mousemove --sync {center_x} {center_y}")
        if clicks > 0:
            print(f"xdotool click --repeat {clicks} 1")
            os.system(f"xdotool click --repeat {clicks} 1")

    else:  # help
        print(title + usage)
