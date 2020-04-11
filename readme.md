# uniclick

Click on any text using just your keyboard. `uniclick` takes a
screenshot of your desktop, runs optical character recognition (OCR)
on it, then provides you with a narrowing UI select a word. Once
complete, you cursor will be moved to the center of your selected
word. It wlil also click and double-click on request.

Here's a demo:

![uniclick demo](./demo.gif)

The UI works by overlaying dark boxes over each word the OCR engine has
detected. You build up a search string by typing letters or numbers (all
other characters are ignored). As you do so, uniclick will only highlight
words that start with your search string. Pressing `<backspace>` will
delete the last character you typed. Once there are less than 5 words
highlighted, you can also press `<tab>` to cycle between them. The selected
word is surrounded by an extra border. Once you have selected the word
you want, type `<enter>` to finish. The cursor will be moved to the center
of that word.

I don't think this is an intended use case of tesseract, so the OCR does get
quite a few errors. If you've typed `unicl` and the word `uniclick` stops being
highlighted, it's probably because the `l` has been misread. Try pressing
`<backspace>` then `1` and seeing if it stays highlighted. 

If you want to give up/cancel, press `<esc>` at any time.

It expects to be inside an x11 session with a compositor running. I've
only tested this on Ubuntu 19.04 running i3 and compton.

System requirements:
  - tesseract
  - xdotool
  - scrot
  - python3

Python requirements are in requirements.txt.

Example setups for i3:
  1. Scan screen then use overlay ui for picking (zenity is used for a
     progress indicator, but thats optional).
        ```
        bindsym $mod+c exec uniclick update \\
            | zenity --progress --auto-close --auto-kill --pulsate \\
                     --text "uniclick loading..." \\
            && uniclick ui
        ```

  2. Scan screen then use overlay ui for picking. uniclick will
     continue to scan in the background, allowing quick response times
     for future invocations.
        ```
        bindsym $mod+c exec uniclick update --daemon && uniclick ui
        ```

There are tradeoffs between these options:
  - Running the update as a daemon means it'll be responsive, but
    you'll waste a lot compute and there's a high likelihood that the
    cached data is out of date.
  - Running the update on demand shouldn't ever give out of date
    results, but will be slow (each update takes around 5 seconds on
    my machine).


Credits:
  - [This gist](https://gist.github.com/initbrain/6628609) was vital for me getting the overlay
    window to work.
  - [This stack overflow answer](https://stackoverflow.com/questions/14200512#14269915) pointed me towards using
    the composite overlay window which made the ui reliable enough to actually be used.
  - tesseract, pyocr, xdotool, pillow, python-xlib, etc for doing the hard work..
