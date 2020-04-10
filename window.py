from Xlib import X, display, XK

class Window:
    def __init__(self, display):
        self.display = display
        self.screen = self.display.screen()
        self.window = self.screen.root

        cursor = X.NONE

        self.window.grab_keyboard(
            1,
            X.GrabModeAsync,
            X.GrabModeAsync,
            X.CurrentTime,
        )

        colormap = self.screen.default_colormap
        self.color = colormap.alloc_color(0, 0, 0)
        self.xor_color = self.color.pixel ^ 0xffffff

        self.gc = self.window.create_gc(
            foreground=self.xor_color,
            graphics_exposures=False,
            function=X.GXxor,
            subwindow_mode=X.IncludeInferiors,
        )

        self.window.change_attributes(event_mask=X.ExposureMask)

    def draw(self, word_boxes):
        for word, box in word_boxes:
            top_left, bottom_right = box

            x, y = top_left
            width, height = abs(top_left[0]-bottom_right[0]), abs(top_left[1]-bottom_right[1])

            self.window.fill_rectangle(self.gc, x-1, y-1, width+2, height+2)
