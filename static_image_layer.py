# static_image_layer.py
from pico2d import load_image, get_canvas_width, get_canvas_height

class StaticImageLayer:
    def __init__(self, image_path: str):
        self.image = load_image(image_path)
        self._recalc_fit()

    def _recalc_fit(self):
        cw, ch = get_canvas_width(), get_canvas_height()
        iw, ih = self.image.w, self.image.h


        s = min(cw / iw, ch / ih)


        self.dw = iw * s
        self.dh = ih * s


        self.cx = (cw - self.dw) * 0.5 + self.dw * 0.5
        self.cy = (ch - self.dh) * 0.5 + self.dh * 0.5


    def update(self):
        self._recalc_fit()

    def draw(self):

        self.image.draw(self.cx, self.cy, self.dw, self.dh)

    def get_bb(self):
        return 0, 0, 0, 0