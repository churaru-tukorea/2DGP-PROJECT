import random
from pico2d import load_image, get_canvas_width

class Sword:

    def __init__(self, ground_y: int, x: int | None = None):
        self.image = load_image('real_sword.png')
        cw = get_canvas_width()
        self.x = x if x is not None else random.randint(40, cw - 40)

        self.ground_y = ground_y
        self.embed_px = 10  # 땅에 박힌 깊이
        self.draw_w = 20  # 화면에 보이는 폭
        self.draw_h = 80  # 화면에 보이는 높이

    def update(self):
        pass

    def draw(self):
        #바닥에 박혀 보이도록 중심 y를 살짝 내린다.
        y = self.ground_y + (self.draw_h // 2) - self.embed_px
        self.image.draw(self.x, y, self.draw_w, self.draw_h)

    def get_bb(self):
        pass

    def handle_collision(self, group, other):
        pass