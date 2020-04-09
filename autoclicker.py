import autopy
import pyocr
import pyocr.builders
import pygtrie
import time

from PIL import Image

tools = pyocr.get_available_tools()
tool = tools[1]  # libtesseract

langs = tool.get_available_languages()
lang = langs[0]

autopy.bitmap.capture_screen().save("screenshot.png")
screen = Image.open("screenshot.png")

word_boxes = tool.image_to_string(
    screen,
    lang=lang,
    builder=pyocr.builders.WordBoxBuilder(),
)

word_to_box = {word_box.content.lower(): word_box.position for word_box in word_boxes}
word_to_box = pygtrie.Trie(word_to_box)

search_term = ""
boxes = list(word_to_box.itervalues(''))
while len(boxes) > 1:
    search_term += input("search: " + search_term)
    boxes = list(word_to_box.itervalues(search_term.lower()))
    print("results: " + ", ".join([''.join(tup) for tup in word_to_box.iterkeys(search_term)]))

[box] = boxes
top_left, bottom_right = box
center = (top_left[0] + bottom_right[0])/2, (top_left[1] + bottom_right[1])/2

autopy.mouse.move(center[0]/autopy.screen.scale(), center[1]/autopy.screen.scale())
autopy.mouse.click(autopy.mouse.Button.LEFT)
