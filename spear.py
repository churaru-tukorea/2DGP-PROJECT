import random, math
from pico2d import load_image, get_canvas_width, get_time, draw_rectangle, draw_line
import game_world, game_framework
from spear_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX


NATIVE_SPRITE_DEG = -34.0

class Spear:
    def __init__(self, ground_y: int, x: int | None = None):
        self.image = load_image('spear.png')
        cw = get_canvas_width()
        self.x = x if x is not None else random.randint(40, cw - 40)
        self.ground_y = ground_y

        self.draw_w = 40
        self.draw_h = 80
        self.embed_px = 10
        self.y = self.ground_y + (self.draw_h - self.embed_px) * 0.5

        self.state = 'GROUND'
        self.owner = None

        self.native_rad = math.radians(NATIVE_SPRITE_DEG)
        self.sprite_flip = ''  # 던질 때의 플립 저장용
        self.no_stage_hit_until = 0.0  # FLYING 직후 일정 시간 바닥 충돌 무시용 타이머
        # 투척 물리
        self.vx = 0.0
        self.vy = 0.0
        self.rad = math.radians(0.0)
        self.speed = 1200.0  # 매우 빠르게
        self.gravity = -900.0
        self.life_time = 1.2
        self.spawn_time = get_time()

        self.ignore_char = None
        self.ignore_until = 0.0

        self.col_w = 12  # ← 충돌 전용 폭
        self.col_h = self.draw_h-10  # 충돌 높이는 보이는 높이와 같게

        self._parry_lock = False  # 동일 프레임 중복 히트 방지

    def handle_collision(self, group, other):
        # 캐릭터 쪽에서 대부분 처리함. 창 쪽은 특별히 할 일 없음.
        if group == 'attack_spear:char':
            # 던진 직후 자기 소유자와 충돌 무시
            if (other is self.ignore_char) and (get_time() <= self.ignore_until):
                return
            if getattr(other, 'parry_active', False):
                self._parry_lock = True
                self.reset_to_ground_random()
        if group == 'attack_spear:stage' and self.state == 'FLYING':
            now = get_time()
            if now < self.no_stage_hit_until:
                return
            self.reset_to_ground_random()
            return
        return

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
        if self.state != 'EQUIPPED' or not self.owner:
            return

        pose = self._compute_equipped_pose()
        if not pose:
            return

        cx, cy, rad, _flip, dw, dh, *_ = pose

        # 던지기 시작 위치/각도는 마지막 장착 포즈 기준
        self.state = 'FLYING'
        self.x, self.y = cx, cy
        self.rad = rad  # 애니메이션 마지막 프레임 각도 그대로 사용

        # 이동 방향은 얼굴 방향만 반영해서 수평 이동만 하도록
        dir_sign = 1 if self.owner.face_dir == 1 else -1
        self.vx = self.speed * dir_sign
        self.vy = 0.0

        self.spawn_time = get_time()

        # 캐릭터 몸에서 살짝 떨어진 위치에서 시작 (자기 몸에 바로 닿지 않게)
        offset = (dw * 0.5) + 20
        self.x += math.cos(self.rad) * offset
        #self.y += math.sin(self.rad) * offset*-1

        now = get_time()
        self.spawn_time = now

        NO_STAGE_HIT_GRACE = 0.25  # 원하는 만큼 조절 (초)
        self.no_stage_hit_until = now + NO_STAGE_HIT_GRACE

        # 손에서 완전히 떨어지게 owner 연동 해제
        self.detach()

#검처럼 땅에 랜덤하게 박히는
    def reset_to_ground_random(self):
        print('[RESET_TO_GROUND_RANDOM]', 'state=', self.state, 'x=', self.x, 'y=', self.y)
        cw = get_canvas_width()
        self.x = random.randint(40, cw - 40)
        # ★ 빠졌던 줄: GROUND로 돌아갈 때는 y도 바닥 기준으로 재설정
        self.y = self.ground_y + (self.draw_h - self.embed_px) * 0.5

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
            #self.vy += self.gravity * dt
            self.x += self.vx * dt
            #self.y += self.vy * dt

            # 수명/화면 밖 → 빗나감 처리
            cw = get_canvas_width()
            if (now - self.spawn_time > self.life_time or
                    self.x < -100 or self.x > cw + 100):
                self.reset_to_ground_random()

        pass
    def draw(self):
        # 디버그 AABB
        l, b, r, t = self.get_bb()
        #draw_rectangle(l, b, r, t)

        if self.state == 'EQUIPPED' and self.owner:
            if self.owner.action in ('jump_up', 'jump_fall', 'jump_land'):
                return
            cx, cy, rad, flip, dw, dh, hx, hy = self._compute_equipped_pose()
            self.image.clip_composite_draw(0, 0, self.image.w, self.image.h, rad, flip, cx, cy, dw, dh)
            self._debug_draw_obb()
            #draw_rectangle(hx - 2, hy - 2, hx + 2, hy + 2)
            return

        if self.state == 'GROUND':
            self.image.clip_composite_draw(
                0, 0, self.image.w, self.image.h,
                math.radians(180), '', self.x, self.y,
                self.draw_w, self.draw_h
            )
            print('spear GROUND', self.x, self.y)
            self._debug_draw_obb()
            return

        if self.state == 'EQUIPPED' and self.owner:
            cx, cy, rad, flip, dw, dh, hx, hy = self._compute_equipped_pose()
            self.image.clip_composite_draw(0, 0, self.image.w, self.image.h, rad, flip, cx, cy, dw, dh)
            self._debug_draw_obb()
            #draw_rectangle(hx - 2, hy - 2, hx + 2, hy + 2)  # 손 디버그
            return

        if self.state == 'FLYING':
            self.image.clip_composite_draw(
                0, 0, self.image.w, self.image.h,
                self.rad, '', self.x, self.y, self.draw_w, self.draw_h

            )
            print('spear FLYING', self.x, self.y)
            self._debug_draw_obb()
        self._debug_draw_obb()

    def _debug_draw_obb(self):
        pts = self.get_obb()
        for i in range(4):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % 4]
            draw_line(int(x1), int(y1), int(x2), int(y2))



    def get_bb(self):
        if self.state == 'GROUND':
            hw, hh = self.draw_w * 0.5, self.draw_h * 0.5
            return self.x - hw, self.y - hh, self.x + hw, self.y + hh
            # EQUIPPED/FLYING 은 OBB → AABB 근사
        xs = [p[0] for p in self.get_obb()]
        ys = [p[1] for p in self.get_obb()]
        return min(xs), min(ys), max(xs), max(ys)

    def get_obb(self):
        # 땅에 박힌 상태는 그냥 AABB 그대로 쓰면 충분
        if self.state == 'GROUND':
            l, b, r, t = self.get_bb()
            return ((l, b), (r, b), (r, t), (l, t))

        # EQUIPPED 이고 owner가 있으면 손 기준 포즈 사용
        if self.state == 'EQUIPPED' and self.owner:
            pose = self._compute_equipped_pose()
            if pose:
                cx, cy, rad, _flip, dw, dh, *_ = pose
            else:
                cx, cy, rad, dw, dh = self.x, self.y, self.rad, self.draw_w, self.draw_h
        else:
            # FLYING 포함: 현재 위치 + 현재 회전각 + draw 크기를 기준으로
            cx, cy, rad, dw, dh = self.x, self.y, self.rad, self.draw_w, self.draw_h
        total_rad = rad + self.native_rad
        # 스프라이트 전체보다 조금 작게 충돌 박스 설정
        col_w = dw * 0.30  # 너비 줄여서 막대처럼
        col_h = dh * 0.90  # 높이는 거의 그대로

        hw, hh = col_w * 0.5, col_h * 0.5
        c, s = math.cos(total_rad), math.sin(total_rad)

        # 시계 방향 순서로 4꼭짓점
        return (
            (cx - hw * c + hh * s, cy - hw * s - hh * c),
            (cx + hw * c + hh * s, cy + hw * s - hh * c),
            (cx + hw * c - hh * s, cy + hw * s + hh * c),
            (cx - hw * c - hh * s, cy - hw * s + hh * c),
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

        # 이미지 원본 높이를 self.draw_h에 맞추는 스케일
        scale = self.draw_h / float(sh)
        dw = int(sw * scale)   # 폭은 비율에 맞춰
        dh = self.draw_h       # 높이는 항상 80 (위에서 정한 값)


        dx, dy = PIVOT_FROM_CENTER_PX
        dx *= scale
        dy *= scale

        rad = math.radians(deg_prime)
        rx = dx * math.cos(rad) - dy * math.sin(rad)
        ry = dx * math.sin(rad) + dy * math.cos(rad)

        cx = hx + rx
        cy = hy + ry

        return cx, cy, rad, flip, dw, dh, hx, hy

