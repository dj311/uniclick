import os
import json
import autoclickerd
import sys


if __name__=="__main__":
    num_args = len(sys.argv) - 1
    if num_args == 0:
        word_to_box = autoclickerd.ocr_screen()
        print("\n".join(word_to_box.keys()))

        f = open(autoclickerd.SCREEN_JSON, "w")
        json.dump(word_to_box, f)
        f.close()

        quit(1)

    elif num_args == 1:
        f = open(autoclickerd.SCREEN_JSON, "r")
        word_to_box = json.load(f)
        f.close()

        word = sys.argv[1]
        box = word_to_box.get(word)
        if box is None:
            print("couldn't find requested box")

        top_left, bottom_right = box

        center_x = (top_left[0] + bottom_right[0])/2
        center_y = (top_left[1] + bottom_right[1])/2

        print("going to", center_x, center_y)

        os.system("xdotool mousemove --sync " + str(int(center_x)) + " " + str(int(center_y)))

