import os
import json
import autoclickerd

f = open(autoclickerd.SCREEN_JSON, "r")
word_to_box = json.load(f)
f.close()

search_term = ""
stop = False
while len(word_to_box) > 1 and not stop:
    search_term += input("search: " + search_term)
    if search_term.endswith("$"):
        stop = True
        search_term = search_term.rstrip("$")

    if stop:
        word_to_box = {
            word: box for word, box in word_to_box.items()
            if word == search_term
        }
        first, *rest = list(word_to_box.items())
        word_to_box = dict([first])

    else:
        word_to_box = {
            word: box for word, box in word_to_box.items()
            if word.startswith(search_term)
        }

    print("results: " + ", ".join(word_to_box.keys()))

if len(word_to_box) == 0:
    print("couldn't find matching text")

else:
    box, *rest = list(word_to_box.values())
    top_left, bottom_right = box

    center_x = (top_left[0] + bottom_right[0])/2
    center_y = (top_left[1] + bottom_right[1])/2

    center_x = center_x/autoclickerd.SCALE_PIXELS
    center_y = center_y/autoclickerd.SCALE_PIXELS

    print(center_x, center_y)

    os.system("xdotool mousemove --sync " + str(int(center_x)) + " " + str(int(center_y)))
