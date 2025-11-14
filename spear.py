import random, math
from pico2d import load_image, get_canvas_width, get_time, draw_rectangle, draw_line
import game_world, game_framework
from spear_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX


NATIVE_SPRITE_DEG = -20.0

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
        self.speed = 600.0  # 매우 빠르게
        self.gravity = -900.0
        self.life_time = 1.2
        self.spawn_time = get_time()

        self.ignore_char = None
        self.ignore_until = 0.0

        self.col_w = 12  # ← 충돌 전용 폭
        self.col_h = self.draw_h-10  # 충돌 높이는 보이는 높이와 같게

        self._parry_lock = False  # 동일 프레임 중복 히트 방지

        self.no_char_hit_until = 0.0  # 캐릭터 충돌 유예
        self._owner_release_time = 0.0  # 임시 owner 유지 종료 시각



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

        cx, cy, draw_rad, flip, dw, dh, *_ = pose

        # draw → phys 환원해서 비행에 사용
        native = self.native_rad if flip == '' else -self.native_rad
        phys_rad = draw_rad + native

        old_owner = self.owner
        self.state = 'FLYING'
        self.x, self.y = cx, cy
        self.rad = phys_rad  # ← 비행/충돌용은 'phys'
        self.sprite_flip = flip  # ← 비행 중 렌더용 플립 기억

        dir_sign = 1 if old_owner.face_dir == 1 else -1
        self.vx = self.speed * dir_sign
        self.vy = 0.0

        offset = (dw * 0.5) + 20
        self.x += math.cos(self.rad) * offset

        now = get_time()
        self.spawn_time = now

        GRACE = 0.18
        self.no_stage_hit_until = now + GRACE
        self.no_char_hit_until = now + GRACE
        self.ignore_char = old_owner
        self.ignore_until = now + GRACE

        if getattr(old_owner, 'weapon', None) is self:
            old_owner.weapon = None
        self._owner_release_time = now + GRACE
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

        # 동적 충돌 그룹: FLYING 이라도 캐릭터 충돌은 GRACE 뒤에만 켠다
        try:
            if self.state == 'FLYING' and now >= self.no_char_hit_until:
                game_world.remove_collision_object_once(self, 'attack_spear:char')
                game_world.add_collision_pair('attack_spear:char', self, None)
            else:
                game_world.remove_collision_object_once(self, 'attack_spear:char')
        except Exception:
            pass

        # 임시 owner 해제(유예 끝나면 owner=None)
        if self.state == 'FLYING' and self.owner and now >= self._owner_release_time:
            self.owner = None

        if self.state == 'FLYING':
            dt = game_framework.frame_time
            # 중력 없이 수평 비행(요구사항 유지)
            self.x += self.vx * dt

            cw = get_canvas_width()
            if (now - self.spawn_time > self.life_time) or (self.x < -100) or (self.x > cw + 100):
                self.reset_to_ground_random()


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
            # 비행 중: self.rad(phys) → draw로 보정
            flip = self.sprite_flip if self.sprite_flip else ('' if self.vx >= 0 else 'h')
            native = self.native_rad if flip == '' else -self.native_rad
            draw_rad = self.rad - native

            self.image.clip_composite_draw(
                0, 0, self.image.w, self.image.h,
                draw_rad, flip, self.x, self.y, self.draw_w, self.draw_h
            )
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
        if self.state == 'GROUND':
            l, b, r, t = self.get_bb()
            return ((l, b), (r, b), (r, t), (l, t))

        if self.state == 'EQUIPPED' and self.owner:
            pose = self._compute_equipped_pose()
            if pose:
                cx, cy, draw_rad, flip, dw, dh, *_ = pose
                # draw → phys 환원
                native = self.native_rad if flip == '' else -self.native_rad
                rad = draw_rad + native
            else:
                cx, cy, rad, dw, dh = self.x, self.y, self.rad, self.draw_w, self.draw_h
        else:
            cx, cy, rad, dw, dh = self.x, self.y, self.rad, self.draw_w, self.draw_h

        col_w = dw * 0.30
        col_h = dh * 0.90
        hw, hh = col_w * 0.5, col_h * 0.5
        c, s = math.cos(rad), math.sin(rad)
        return (
            (cx - hw * c + hh * s, cy - hw * s - hh * c),
            (cx + hw * c + hh * s, cy + hw * s - hh * c),
            (cx + hw * c - hh * s, cy + hw * s + hh * c),
            (cx - hw * c - hh * s, cy - hw * s + hh * c),
        )
    def _compute_equipped_pose(self):
        owner = self.owner
        cur = owner._current_frame_info()
        if not cur:
            return owner.x, owner.y, 0.0, '', self.draw_w, self.draw_h, owner.x, owner.y
        act, idx, (fw, fh) = cur

        lst = POSE.get(act)
        if not lst or idx >= len(lst):
            return owner.x, owner.y, 0.0, '', self.draw_w, self.draw_h, owner.x, owner.y

        ox_src, oy_src = lst[idx]['offset_src_px']
        base_deg = lst[idx]['deg']  # 포즈가 정의한 '물리 각도'

        sx = owner.draw_w / float(max(fw, 1))
        sy = owner.draw_h / float(max(fh, 1))

        if owner.face_dir == 1:
            hx = owner.x - owner.draw_w * 0.5 + ox_src * sx
            phys_deg, flip = base_deg, ''
            native_deg_signed = NATIVE_SPRITE_DEG  # 우향은 그대로
        else:
            hx = owner.x + owner.draw_w * 0.5 - ox_src * sx
            if LEFT_FLIP_RULE == 'NEGATE':
                phys_deg, flip = -base_deg, 'h'
            elif LEFT_FLIP_RULE == 'KEEP':
                phys_deg, flip = base_deg, 'h'
            else:
                phys_deg, flip = base_deg + 180.0, 'h'
            native_deg_signed = -NATIVE_SPRITE_DEG  # 좌향은 부호 반전

        hy = owner.y - owner.draw_h * 0.5 + oy_src * sy

        # === 핵심: draw용 각도와 phys용 각도 분리 ===
        phys_rad = math.radians(phys_deg)  # 충돌/OBB
        draw_rad = math.radians(phys_deg - native_deg_signed)  # 렌더/피벗

        sw, sh = self.image.w, self.image.h
        scale = self.draw_h / float(sh)
        dw = int(sw * scale)
        dh = self.draw_h

        # 손잡이 피벗(이미지 좌표 → 월드) 회전은 "그리는 각도"로 해야 맞다
        dx, dy = PIVOT_FROM_CENTER_PX
        dx *= scale;
        dy *= scale
        rx = dx * math.cos(draw_rad) - dy * math.sin(draw_rad)
        ry = dx * math.sin(draw_rad) + dy * math.cos(draw_rad)

        cx = hx + rx
        cy = hy + ry

        # draw_rad만 반환(렌더용). phys는 필요 시 flip과 native로 복구.
        return cx, cy, draw_rad, flip, dw, dh, hx, hy

    def pickup_spear(self, other):
        if self.weapon: return
        self.weapon = other
        game_world.remove_collision_object_once(other, 'char:spear')
        other.attach_to(self)
        other.state = 'EQUIPPED'
        self.weapon_pick_time = get_time()  # ← 추가
        return

