# static_image_layer.py
from pico2d import load_image, get_canvas_width, get_canvas_height

class StaticImageLayer:
    def __init__(self, image_path: str, fit: str = 'contain'):
        self.image = load_image(image_path)
        self.fit = fit  # 'contain' or 'cover'
        self._recalc_fit()

    def _recalc_fit(self):
        cw, ch = get_canvas_width(), get_canvas_height()
        iw, ih = self.image.w, self.image.h

        if self.fit == 'cover':
            s = max(cw / iw, ch / ih)   # 화면을 꽉 채움(일부 잘림 허용)
        else:
            s = min(cw / iw, ch / ih)   # 전체 보이기(여백 허용)

        self.dw = iw * s
        self.dh = ih * s
        self.cx = (cw - self.dw) * 0.5 + self.dw * 0.5
        self.cy = (ch - self.dh) * 0.5 + self.dh * 0.5 - 20

    def update(self):
        self._recalc_fit()

    def draw(self):
        self.image.draw(self.cx, self.cy, self.dw, self.dh)

    def get_bb(self):
        return 0, 0, 0, 0