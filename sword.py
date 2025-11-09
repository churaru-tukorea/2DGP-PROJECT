import random
from pico2d import load_image, get_canvas_width, draw_rectangle
import math


class Sword:

    def __init__(self, ground_y: int, x: int | None = None):
        self.image = load_image('real_sword.png')
        cw = get_canvas_width()
        self.x = x if x is not None else random.randint(40, cw - 40)

        self.ground_y = ground_y
        self.embed_px = 10  # 땅에 박힌 깊이
        self.draw_w = 20  # 화면에 보이는 폭
        self.draw_h = 80  # 화면에 보이는 높이

        self.y = self.ground_y + (self.draw_h - self.embed_px) * 0.5
        self.state = 'GROUND'
        self.owner = None

    def update(self):
        pass

    def draw(self):
        if self.state != 'GROUND': return
        # 바닥에 박힌 느낌으로 약간 기울여 그림(연출)
        self.image.clip_composite_draw(0, 0, self.image.w, self.image.h,
                                       3.14159, '', self.x, self.y,
                                       self.draw_w, self.draw_h)
        draw_rectangle(*self.get_bb())

    def get_bb(self):
        if self.state != 'GROUND':
            return -9999,-9999,-9998,-9998
        half_w = self.draw_w * 0.5
        half_h = self.draw_h * 0.5

        return self.x - half_w, self.y - half_h, self.x + half_w, self.y + half_h

    def handle_collision(self, group, other):
        if group == 'char:sword' and self.state == 'GROUND':
            print('캐릭터가 검을 주웠습니다!')
            # 실제 장착 처리는 Character 쪽에서 한다.



    def attach_to(self, owner):
        self.state = 'EQUIPPED'
        self.owner = owner


    def detach(self):
        self.owner = None



    def reset_to_ground_random(self):
    # "처음 생성될 때처럼" 랜덤 X로 바닥 리스폰
      cw = get_canvas_width()
      self.x = random.randint(40, cw - 40)
      self.state = 'GROUND'
      self.detach()
