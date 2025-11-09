import random
from pico2d import load_image, get_canvas_width, draw_rectangle, draw_line
import math
from sword_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX
from character import Character
import game_world

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
        try:
            if self.state == 'EQUIPPED' and self.owner:
                # 중복 방지: 먼저 제거 후 한 번만 추가
                game_world.remove_collision_object_once(self, 'attack_sword:char')
                game_world.add_collision_pair('attack_sword:char', self, None)
            else:
                game_world.remove_collision_object_once(self, 'attack_sword:char')
        except Exception:
            pass

    def draw(self):
        l, b, r, t = self.get_bb()
        draw_rectangle(l, b, r, t)
        cs = self.get_obb()
        for i in range(4):
             x1,y1 = cs[i]; x2,y2 = cs[(i+1)%4]
             draw_line(x1,y1, x2,y2)

        if self.state == 'GROUND':
            self.image.clip_composite_draw(0, 0, self.image.w, self.image.h,
                                           3.14159, '', self.x, self.y,
                                           self.draw_w, self.draw_h)
            return

        if self.state == 'EQUIPPED' and self.owner:
            pose = self._compute_equipped_pose()
            if not pose:
                return
            cx, cy, rad, flip, dw, dh, hx, hy, aabb = pose
            self.image.clip_composite_draw(0, 0, self.image.w, self.image.h,
                                           rad, flip, cx, cy, dw, dh)
            # 손 지점 디버그(작은 점)
            draw_rectangle(hx - 2, hy - 2, hx + 2, hy + 2)
            return

    def get_obb(self):
        if self.state == 'EQUIPPED' and self.owner:
            cx, cy, rad, _flip, dw, dh, *_ = self._compute_equipped_pose()
            hw, hh = dw*0.5, dh*0.5
            c, s = math.cos(rad), math.sin(rad)
            return (
                (cx +(+hw)*c -(+hh)*s, cy +(+hw)*s +(+hh)*c),
                (cx +(+hw)*c -(-hh)*s, cy +(+hw)*s +(-hh)*c),
                (cx +(-hw)*c -(-hh)*s, cy +(-hw)*s +(-hh)*c),
                (cx +(-hw)*c -(+hh)*s, cy +(-hw)*s +(+hh)*c),
            )
        l,b,r,t = self.get_bb()
        return ((l,b),(r,b),(r,t),(l,t))

    def get_bb(self):
        if self.state == 'GROUND':
            half_w = self.draw_w * 0.5
            half_h = self.draw_h * 0.5
            return self.x - half_w, self.y - half_h, self.x + half_w, self.y + half_h

        if self.state == 'EQUIPPED' and self.owner:
            pose = self._compute_equipped_pose()
            if pose:
                cx, cy, rad, _flip, dw, dh, _hx, _hy, _aabb = pose
                hw, hh = dw * 0.5, dh * 0.5
                return cx - hw, cy - hh, cx + hw, cy + hh

        return -9999, -9999, -9998, -9998

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
      cw = get_canvas_width()
      self.x = random.randint(40, cw - 40)
      self.state = 'GROUND'
      self.detach()
      try:
        import game_world
        game_world.remove_collision_object_once(self, 'attack_sword:char')
      except:
        pass

    def _compute_equipped_pose(self):
        owner = self.owner
        info = owner._current_frame_info()
        if not info:
            return None
        act, idx, (fw, fh) = info

        lst = POSE.get(act)
        if not lst or idx >= len(lst):
            return None
        ox_src, oy_src = lst[idx]['offset_src_px']
        deg = lst[idx]['deg']


        sx = owner.draw_w / float(max(fw,1))
        sy = owner.draw_h / float(max(fh,1))


        if owner.face_dir == 1:
            hx = owner.x - owner.draw_w * 0.5 + ox_src * sx
            deg_prime, flip = deg, ''
        else:
            hx = owner.x + owner.draw_w * 0.5 - ox_src * sx
            if LEFT_FLIP_RULE == 'NEGATE':
                deg_prime, flip = -deg, 'h'
            elif LEFT_FLIP_RULE == 'KEEP':
                deg_prime, flip = deg, 'h'
            else:  # 'ADD_PI'
                deg_prime, flip = deg + 180.0, 'h'
        hy = owner.y - owner.draw_h * 0.5 + oy_src * sy


        scale = owner.draw_h / 40.0
        dw, dh = int(self.image.w * scale), int(self.image.h * scale)
        dx, dy = PIVOT_FROM_CENTER_PX
        dx *= scale; dy *= scale
        rad = math.radians(deg_prime)
        rx = dx * math.cos(rad) - dy * math.sin(rad)
        ry = dx * math.sin(rad) + dy * math.cos(rad)


        cx = hx + rx
        cy = hy + ry


        aabb = self._aabb_from_center(cx, cy, dw, dh, rad)
        return cx, cy, rad, flip, dw, dh, hx, hy, aabb

    @staticmethod
    def _aabb_from_center(cx, cy, w, h, rad):
        hw, hh = w*0.5, h*0.5
        c, s = math.cos(rad), math.sin(rad)
        pts = []
        for sx, sy in ((+hw,+hh),(+hw,-hh),(-hw,+hh),(-hw,-hh)):
            wx = cx + sx*c - sy*s
            wy = cy + sx*s + sy*c
            pts.append((wx, wy))
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

