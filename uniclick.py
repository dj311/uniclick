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
             ui :: list and goto word via an overlay ui. results are narrowed
                   by typing letters (narrowing is case insensitive and only
                   considers 'qwertyuiopasdfghjklzxcvbnm1234567890'.
                   - <tab> cycles between results when you have 5 or less.
                     unfortunately the cycling order is a little stochastic.
                   - <backspace> untypes letters (as you'd expect).
                   - <enter> completes the search.
                   the default action is to move the mouse. the argument --click
                   will click after moving and --double-click will click twice.
           help :: show this message.

system requirements:
  - tesseract
  - xdotool
  - scrot
  - python3

python requirements are in requirements.txt.

example setups for i3:

  1. scan then use overlay ui for picking
        bindsym $mod+c exec uniclick update \
            | zenity --progress --text "uniclick loading..." --auto-close --auto-kill --pulsate \
            && uniclick ui

  2. configure i3 to scan then search when $mod+m is pressed:
         bindsym $mod+m exec uniclick update \
            | zenity --progress --text "uniclick loading..." --auto-close --auto-kill --pulsate \
            && uniclick goto "$(uniclick list | rofi -dmenu -p 'uniclick' -i)"

  3. constantly scan screen in background then search cached version on demand:
         bindsym $mod+m exec uniclick update --daemon \
            && uniclick goto "$(uniclick list | rofi -dmenu -p 'uniclick' -i)"

there are tradeoffs between the different options:
  - running `uniclick update` as a daemon means that it's be responsive, but you'll waste a lot compute
and there's a high likelihood of the cached data being out of date.
  - running `uniclick update` on demand shouldn't ever give out of
    date results, but will be slow (approx 5 secs on my machine).
  - the overlay ui is considerably better, but can be buggy.


"""
__doc__ = title + usage

import daemon
import json
import os
import pyocr
import pyocr.builders
import sys
import time
import window

from Xlib import X, XK
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
    return ''.join(c for c in word.lower() if c in ALPHABET)

def ocr_screen():
    os.system(f"scrot -q 100 --overwrite {SCREEN_PNG}.new.png")

    screen_changed = True  # TODO: do an image diff here
    if screen_changed:
        os.system(f"mv {SCREEN_PNG}.new.png {SCREEN_PNG}")

        screen = Image.open(SCREEN_PNG).convert('L')
        screen = ImageEnhance.Contrast(screen).enhance(1.5)

        word_boxes = tool.image_to_string(
            screen,
            lang=lang,
            builder=pyocr.builders.WordBoxBuilder(),
        )
        word_to_box = {word_box.content: word_box.position for word_box in word_boxes}

    else:
        print("screen hasn't changed")
        f = open(SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

    return word_to_box


if __name__=="__main__":
    command, *args = sys.argv[1:]

    if command == 'update' and args == ["--daemon"]:
        with daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(DAEMON_PID)):
            while True:
                word_to_box = ocr_screen()

                f = open(SCREEN_JSON, "w")
                json.dump(word_to_box, f)
                f.close()

                time.sleep(3)

    elif command == 'update' and args == []:
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
        center_x, center_y = int(center_x), int(center_y)

        os.system(f"xdotool mousemove --sync {center_x} {center_y}")

    elif command in ("help", "-h", "h", "--help", "-help"):
        print(title + usage)

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

        w = window.Window(window.display.Display())
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

                elif keysym == XK.XK_Return:
                    found = True

                elif keysym == XK.XK_Tab:
                    if selection is not None:
                        selection += 1

                filtered_boxes = {
                    word: box for word, box in word_to_box.items()
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

        center_x = (top_left[0] + bottom_right[0])/2
        center_y = (top_left[1] + bottom_right[1])/2
        center_x, center_y = int(center_x), int(center_y)

        os.system(f"xdotool mousemove --sync {center_x} {center_y}")
        if clicks > 0:
            print(f"xdotool click --repeat {clicks} 1")
            os.system(f"xdotool click --repeat {clicks} 1")

