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

requirements:
  - tesseract
  - xdotool
  - scrot
  - python3
  - pyocr
  - pillow
  - python-daemon

examples:
  1. configure i3 to scan then search when $mod+m is pressed:
     .config/i3/config:
         bindsym $mod+m exec uniclick update \
            | zenity --progress --text "uniclick loading..." --auto-close --auto-kill --pulsate \
            && uniclick goto "$(uniclick list | rofi -dmenu -p 'uniclick' -i)"

  2. constantly scan screen in background then search cached version on demand:
     .xsession:
         uniclick update --daemon &&
     .config/i3/config:
         bindsym $mod+m exec uniclick update --daemon; uniclick goto "$(uniclick list | rofi -dmenu -p 'uniclick' -i)"

the tradeoff is that 1 is /slow/ to use while 2 feels snappier but is
wasteful and will slow your computer down.

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

        print("going to", center_x, center_y)

        os.system("xdotool mousemove --sync " + str(int(center_x)) + " " + str(int(center_y)))

    elif command in ("help", "-h", "h", "--help", "-help"):
        print(title + usage)

    elif command == "ui":
        f = open(SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

        w = window.Window(window.display.Display())
        w.draw(word_to_box.items())
        w.display.sync()

        search_term = ""
        found = False
        while not found:
            e = w.display.next_event()

            if e.type == X.KeyRelease:
                keysym = w.display.keycode_to_keysym(e.detail, 0)
                string = XK.keysym_to_string(keysym)

                if keysym == XK.XK_BackSpace and len(search_term) > 1:
                    search_term = search_term[0:-1]

                elif keysym == XK.XK_Escape:
                    raise SystemExit

                elif string in ALPHABET:
                    search_term += string

                elif keysym == XK.XK_Return:
                    found = True

                word_to_box = {
                    word: box for word, box in word_to_box.items()
                    if clean_word(word).startswith(clean_word(search_term))
                }

            w.draw(word_to_box.items())
            w.display.sync()

        w.draw(word_to_box.items())
        w.display.sync()

        matches = list(word_to_box.values())
        if len(matches) < 1:
            print("couldn't find requested box")
            exit()

        top_left, bottom_right = matches[0]

        center_x = (top_left[0] + bottom_right[0])/2
        center_y = (top_left[1] + bottom_right[1])/2

        print("going to", center_x, center_y)

        os.system("xdotool mousemove --sync " + str(int(center_x)) + " " + str(int(center_y)))


