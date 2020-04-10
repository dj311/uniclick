from Xlib import X, display, XK

class Window:
    def __init__(self, display):
        self.display = display
        self.screen = self.display.screen()
        self.window = self.screen.root

        cursor = X.NONE

        self.window.grab_pointer(1, X.PointerMotionMask|X.ButtonReleaseMask|X.ButtonPressMask,
                X.GrabModeAsync, X.GrabModeAsync, X.NONE, cursor, X.CurrentTime)
        self.window.grab_keyboard(1, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)

        colormap = self.screen.default_colormap
        self.color = colormap.alloc_color(0, 200, 100)
        # Xor it because we'll draw with X.GXxor function
        self.xor_color = self.color.pixel ^ 0xffffff

        self.gc = self.window.create_gc(
            line_width=2,
            foreground=self.xor_color,
            background=self.screen.black_pixel,
            graphics_exposures=False,
            function = X.GXxor,
            subwindow_mode=X.IncludeInferiors,
        )

        # self.window.map()

    def draw(self, boxes):
        self.window.rectangle(self.gc, 0, 0, 100, 100)

        for box in boxes:
            top_left, bottom_right = box

            x, y = top_left
            width, height = abs(top_left[0]-bottom_right[0]), abs(top_left[1]-bottom_right[1])

            self.window.fill_rectangle(self.gc, x, y, width, height)
