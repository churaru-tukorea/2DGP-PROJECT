import random, math
from pico2d import load_image, get_canvas_width, get_time, draw_rectangle
import game_world, game_framework
from spear_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX

class Spear:
    def __init__(self, ground_y: int, x: int | None = None):
        self.image = load_image('spear.png')
        cw = get_canvas_width()
        self.x = x if x is not None else random.randint(40, cw - 40)
        self.ground_y = ground_y

        self.draw_w = 20
        self.draw_h = 80
        self.embed_px = 10
        self.y = self.ground_y + (self.draw_h - self.embed_px) * 0.5

        self.state = 'GROUND'
        self.owner = None

        # 투척 물리
        self.vx = 0.0
        self.vy = 0.0
        self.rad = math.radians(0.0)
        self.speed = 1200.0  # 매우 빠르게
        self.gravity = -900.0
        self.life_time = 1.2
        self.spawn_time = get_time()

        self._parry_lock = False  # 동일 프레임 중복 히트 방지

    def attach_to(self, owner):
        self.state = 'EQUIPPED'
        self.owner = owner

    def detach(self):
        prev = self.owner
        self.owner = None
        if prev is not None and getattr(prev, 'weapon', None) is self:
            prev.weapon = None
#던져지는
    def throw_from_owner(self):
        if self.state != 'EQUIPPED' or not self.owner: return
        cx, cy, rad, _, dw, dh, *_ = self._compute_equipped_pose()
        self.state = 'FLYING'
        self.spawn_time = get_time()
        dir_x = 1 if self.owner.face_dir == 1 else -1
        self.vx = self.speed * dir_x
        self.vy = +150.0
        self.rad = 0.0
        self.x, self.y = cx, cy
        self.detach()
#검처럼 땅에 랜덤하게 박히는
    def reset_to_ground_random(self):
        cw = get_canvas_width()
        self.x = random.randint(40, cw - 40)
        self.state = 'GROUND'
        self.vx = self.vy = 0.0
        self.rad = math.radians(180.0)
        self.detach()
        try:
            game_world.remove_collision_object_once(self, 'attack_spear:char')
            game_world.add_collision_pair('char:spear', None, self)
        except Exception:
            pass
    def update(self):
        now = get_time()

        # 동적 충돌 그룹 등록(FLYING일 때만 공격판정)
        try:
            if self.state == 'FLYING':
                game_world.remove_collision_object_once(self, 'attack_spear:char')
                game_world.add_collision_pair('attack_spear:char', self, None)
            else:
                game_world.remove_collision_object_once(self, 'attack_spear:char')
        except Exception:
            pass

        if self.state == 'FLYING':
            dt = game_framework.frame_time
            self.vy += self.gravity * dt
            self.x += self.vx * dt
            self.y += self.vy * dt

            # 수명/화면 밖 → 빗나감 처리
            cw = get_canvas_width()
            if (now - self.spawn_time > self.life_time or
                    self.x < -100 or self.x > cw + 100 or
                    self.y < -200):
                self.reset_to_ground_random()

        pass
    def draw(self):
        # 디버그 AABB
        l, b, r, t = self.get_bb()
        draw_rectangle(l, b, r, t)

        if self.state == 'GROUND':
            self.image.clip_composite_draw(
                0, 0, self.image.w, self.image.h,
                math.radians(180), '', self.x, self.y,
                self.draw_w, self.draw_h
            )
            return

        if self.state == 'EQUIPPED' and self.owner:
            cx, cy, rad, flip, dw, dh, hx, hy = self._compute_equipped_pose()
            self.image.clip_composite_draw(0, 0, self.image.w, self.image.h, rad, flip, cx, cy, dw, dh)
            draw_rectangle(hx - 2, hy - 2, hx + 2, hy + 2)  # 손 디버그
            return

        if self.state == 'FLYING':
            self.image.clip_composite_draw(
                0, 0, self.image.w, self.image.h,
                self.rad, '', self.x, self.y, self.draw_w, self.draw_h
            )

    def get_bb(self):
        if self.state == 'GROUND':
            hw, hh = self.draw_w * 0.5, self.draw_h * 0.5
            return self.x - hw, self.y - hh, self.x + hw, self.y + hh
            # EQUIPPED/FLYING 은 OBB → AABB 근사
        xs = [p[0] for p in self.get_obb()]
        ys = [p[1] for p in self.get_obb()]
        return min(xs), min(ys), max(xs), max(ys)
    def get_obb(self):
        if self.state == 'EQUIPPED' and self.owner:
            cx, cy, rad, _flip, dw, dh, *_ = self._compute_equipped_pose()
        elif self.state == 'FLYING':
            cx, cy, rad = self.x, self.y, self.rad
            dw, dh = self.draw_w, self.draw_h
        else:
            l, b, r, t = self.get_bb()
            return ((l, b), (r, b), (r, t), (l, t))

            # Y축 판정 조금 두껍게
        hh_scale = 1.6
        hw, hh = dw * 0.5, dh * 0.5 * hh_scale
        c, s = math.cos(rad), math.sin(rad)
        return (
            (cx + (+hw) * c - (+hh) * s, cy + (+hw) * s + (+hh) * c),
            (cx + (+hw) * c - (-hh) * s, cy + (+hw) * s + (-hh) * c),
            (cx + (-hw) * c - (-hh) * s, cy + (-hw) * s + (-hh) * c),
            (cx + (-hw) * c - (+hh) * s, cy + (-hw) * s + (+hh) * c),
        )
    def _compute_equipped_pose(self):
        owner = self.owner
        cur = owner._current_frame_info()
        if not cur:  # 폴백
            return owner.x, owner.y, 0.0, '', self.draw_w, self.draw_h, owner.x, owner.y
        act, idx, (fw, fh) = cur

        lst = POSE.get(act)
        if not lst or idx >= len(lst):
            return owner.x, owner.y, 0.0, '', self.draw_w, self.draw_h, owner.x, owner.y

        ox_src, oy_src = lst[idx]['offset_src_px']
        deg = lst[idx]['deg']

        sx = owner.draw_w / float(max(fw, 1))
        sy = owner.draw_h / float(max(fh, 1))

        if owner.face_dir == 1:
            hx = owner.x - owner.draw_w * 0.5 + ox_src * sx
            deg_prime, flip = deg, ''
        else:
            hx = owner.x + owner.draw_w * 0.5 - ox_src * sx
            if LEFT_FLIP_RULE == 'NEGATE':
                deg_prime, flip = -deg, 'h'
            elif LEFT_FLIP_RULE == 'KEEP':
                deg_prime, flip = deg, 'h'
            else:
                deg_prime, flip = deg + 180.0, 'h'

        hy = owner.y - owner.draw_h * 0.5 + oy_src * sy

        sw, sh = self.image.w, self.image.h
        scale = owner.draw_h / 50.0
        dw, dh = int(sw * scale), int(sh * scale)

        dx, dy = PIVOT_FROM_CENTER_PX
        dx *= scale;
        dy *= scale
        rad = math.radians(deg_prime)
        rx = dx * math.cos(rad) - dy * math.sin(rad)
        ry = dx * math.sin(rad) + dy * math.cos(rad)
        cx, cy = hx + rx, hy + ry

        return cx, cy, rad, flip, dw, dh, hx, hy




