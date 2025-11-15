import random
from pico2d import load_image, get_canvas_width, draw_rectangle, draw_line, get_time
import math
from sword_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX
from character import Character
import game_world
import game_framework

class Sword:

    def __init__(self, ground_y: int, x: int | None = None):
        self._parry_lock = None
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

#
        self.stage = None  # StageColliders 바인딩용

        self.reset_start_x = self.x
        self.reset_start_y = self.y
        self.reset_target_x = self.x
        self.reset_target_y = self.y
        self.reset_ctrl_x = self.x
        self.reset_ctrl_y = self.y
        self.reset_start_time = 0.0
        self.reset_duration = 0.0

        self.reset_spin_rad = 0.0        # 회전 각도
        self.reset_spin_speed = 0.0      # rad/sec

    def update(self):

        # 리셋 비행 중이면 곡선 이동 / 회전만 처리
        if self.state == 'RESET_FLY':
            self._update_reset_fly()
            return

        if getattr(self, '_parry_lock', False):
            self._parry_lock = False

        try:
            if self.state == 'EQUIPPED' and self.owner and getattr(self.owner, 'action', '') == 'attack_fire':
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
             #draw_line(x1,y1, x2,y2)

        if self.state == 'GROUND':
            self.image.clip_composite_draw(0, 0, self.image.w, self.image.h,
                                           3.14159, '', self.x, self.y,
                                           self.draw_w, self.draw_h)
            return

        if self.state == 'RESET_FLY':
            self.image.clip_composite_draw(
                0, 0, self.image.w, self.image.h,
                self.reset_spin_rad, '',   # 계속 회전
                self.x, self.y,
                self.draw_w, self.draw_h
            )
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
            pose = self._compute_equipped_pose()
            if not pose:
                ox, oy = self.owner.x, self.owner.y
                s = 6
                return ((ox - s, oy - s), (ox + s, oy - s), (ox + s, oy + s), (ox - s, oy + s))
            cx, cy, rad, _flip, dw, dh, *_ = pose
            hw, hh = dw * 0.5, dh * 0.5
            c, s = math.cos(rad), math.sin(rad)
            return (
                (cx + (+hw) * c - (+hh) * s, cy + (+hw) * s + (+hh) * c),
                (cx + (+hw) * c - (-hh) * s, cy + (+hw) * s + (-hh) * c),
                (cx + (-hw) * c - (-hh) * s, cy + (-hw) * s + (-hh) * c),
                (cx + (-hw) * c - (+hh) * s, cy + (-hw) * s + (+hh) * c),
            )
        l, b, r, t = self.get_bb()
        return ((l, b), (r, b), (r, t), (l, t))


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
            # 폴백: 오너 중심의 작은 AABB (디버그·안전용)
            ox, oy = self.owner.x, self.owner.y
            s = 6
            return ox - s, oy - s, ox + s, oy + s

        return -9999, -9999, -9998, -9998
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
        prev = self.owner
        self.owner = None
        # 이전 소유자가 아직 나를 들고 있다고 믿고 있으면 끊어준다
        if prev is not None and getattr(prev, 'weapon', None) is self:
            prev.weapon = None

    def reset_to_ground_random(self):
        """어디선가 날아온 칼을 스테이지 위 랜덤 위치로 곡선 이동시키기."""
        # 이미 리셋 중이면 무시
        if self.state == 'RESET_FLY':
            return

        # 시작 위치 계산
        start_x, start_y = self.x, self.y
        if self.state == 'EQUIPPED' and self.owner:
            pose = self._compute_equipped_pose()
            if pose:
                cx, cy, *_ = pose
                start_x, start_y = cx, cy

        # 기본 타겟 = 지면 랜덤으로 해놓아서 안전빵
        cw = get_canvas_width()
        target_x = random.randint(40, cw - 40)
        target_y = self.ground_y + (self.draw_h - self.embed_px) * 0.5

        # 스테이지가 있으면, 천장 제외 랜덤 플랫폼 위로
        if self.stage is not None:
            try:
                query_bb = (0, -1000, cw, 1000)
                boxes = self.stage.query_boxes(query_bb, margin=0.0)
                if boxes:
                    ground_boxes = [
                        b for b in boxes
                        if ('ceil' not in str(b[0]).lower())
                           and ('wall' not in str(b[0]).lower())
                    ]
                    if not ground_boxes:
                        ground_boxes = boxes
                    _, typ, L, B, R, T = random.choice(ground_boxes)

                    margin_x = self.draw_w * 0.5 + 4
                    if R - L <= margin_x * 2:
                        target_x = (L + R) * 0.5
                    else:
                        target_x = random.uniform(L + margin_x, R - margin_x)

                    target_y = T + (self.draw_h - self.embed_px) * 0.5
            except Exception:
                # 실패하면 그냥 바닥 랜덤 유지
                pass

        self.detach()  # owner.weapon 정리까지 포함

        try:
            game_world.remove_collision_object_once(self, 'attack_sword:char')
            game_world.remove_collision_object_once(self, 'char:sword')
        except Exception:
            pass

        # 5) 베지어 파라미터 넣기(곡선이동을 위해)
        self.reset_start_x = start_x
        self.reset_start_y = start_y
        self.reset_target_x = target_x
        self.reset_target_y = target_y

        mid_x = (start_x + target_x) * 0.5
        base_mid_y = max(start_y, target_y)
        dist_x = abs(target_x - start_x)
        arc_h = max(80.0, dist_x * 0.3)

        self.reset_ctrl_x = mid_x
        self.reset_ctrl_y = base_mid_y + arc_h

        self.reset_start_time = get_time()
        self.reset_duration = 0.9
        self.reset_spin_rad = 0.0
        self.reset_spin_speed = 8.0

        self.state = 'RESET_FLY'
        self.x, self.y = start_x, start_y

    def _update_reset_fly(self):
        now = get_time()
        if self.reset_duration <= 0.0:
            self._finish_reset_landing()
            return

        t = (now - self.reset_start_time) / self.reset_duration
        if t >= 1.0:
            t = 1.0
        one_minus_t = 1.0 - t

        x0, y0 = self.reset_start_x, self.reset_start_y
        x1, y1 = self.reset_ctrl_x, self.reset_ctrl_y
        x2, y2 = self.reset_target_x, self.reset_target_y

        # 베지어를 사용한 식 사용
        self.x = (one_minus_t ** 2) * x0 + 2 * one_minus_t * t * x1 + (t ** 2) * x2
        self.y = (one_minus_t ** 2) * y0 + 2 * one_minus_t * t * y1 + (t ** 2) * y2

        dt = game_framework.frame_time
        self.reset_spin_rad += self.reset_spin_speed * dt

        if t >= 1.0:
            self._finish_reset_landing()

    def _finish_reset_landing(self):
        #타겟 위치에 돌아오면 ground로 전환하는 함수
        self.state = 'GROUND'
        self.x = self.reset_target_x
        self.y = self.reset_target_y
        self.owner = None
        self.reset_spin_rad = 0.0

        try:
            # 공격 판정 제거, 줍기 그룹 다시 등록
            game_world.remove_collision_object_once(self, 'attack_sword:char')
            game_world.add_collision_pair('char:sword', None, self)
        except Exception:
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

    def pickup_sword(self, other):
        if self.weapon:  # 이미 들고 있으면 무시
            return
        self.weapon = other
        game_world.remove_collision_object_once(other, 'char:sword')
        print('무기 장착 (월드 유지, EQUIPPED)')
        other.attach_to(self)
        other.state = 'EQUIPPED'
        self.weapon_pick_time = get_time()  # ← 추가
        return

    def bind_stage(self, stage):
        self.stage = stage

