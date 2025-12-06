from types import SimpleNamespace

from pico2d import (
    load_image, get_time,
    SDL_KEYDOWN, SDL_KEYUP,
    SDLK_SPACE,
    SDLK_LEFT, SDLK_RIGHT,
    SDLK_a, SDLK_d, SDLK_j, SDLK_k, SDLK_p, SDLK_i,
    SDLK_KP_1, SDLK_KP_2, SDLK_KP_3, SDLK_KP_5,
    get_canvas_height, get_canvas_width,
    draw_rectangle, draw_line, load_font,
)

import game_world


import config
# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine
import math

import game_framework


from character_states import (
    Idle, Move, Jump_Up, Jump_Fall, Jump_Land,
    Attack_Fire, Attack_Spear, Parry_Hold,
)


# 공격의 여러 상태를 추가(이게 공격 이후 어떤상태에 갈지도 다 다르기 떄무네)
def attack_ready(e):      return e[0] == 'ATTACK_READY'
def attack_end_air(e):   return e[0] == 'ATTACK_END_AIR'
def attack_end_move(e):   return e[0] == 'ATTACK_END_MOVE'
def attack_end_idle(e):   return e[0] == 'ATTACK_END_IDLE'
def attack_spear_ready(e): return e[0] == 'ATTACK_SPEAR_READY'

def space_down(e): # e is space down ?
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_SPACE

time_out = lambda e: e[0] == 'TIMEOUT'

def right_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_RIGHT


def right_up(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYUP and e[1].key == SDLK_RIGHT


def left_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_LEFT


def left_up(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYUP and e[1].key == SDLK_LEFT

#공격 키
def k_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_k

#점프 시작 키
def j_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_j

#점프키를 땠을떄 거기에 맞게떨어지도록
def j_up(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYUP and e[1].key == SDLK_j

#패링 시작 키
def p_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_p

#패링 마무리 키
def p_up(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYUP and e[1].key == SDLK_p

def i_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_i




class Character:
    def __init__(self, pid=1, keymap=None):
        self.x, self.y = 400, 150 # 이건 그냥 띄워보려는 거니까 일단 임의위치 위에 띄우려는
        self.pid = pid
        #self.font = load_font('ENCR10B.TTF', 16)
        self.move_dir = 0
        if self.pid == 1:
            self.image = load_image('project_character_sheet.png')
        else:  # 2P 이상은 전부 2P 시트 사용
            self.image = load_image('project_character_sheet_2p.png')
        self.move_timer = 0.0

        if keymap is None:
            if pid == 1:
                self.face_dir = +1
                self.keymap = {
                    'left':  [SDLK_a],
                    'right': [SDLK_d],
                    'jump':  [SDLK_j],
                    'attack':[SDLK_k],
                    'spear_attack': [SDLK_i],
                    'parry': [SDLK_p],
                }
            else:  # pid == 2
                self.face_dir = -1
                self.keymap = {

                    'left':  [SDLK_LEFT],
                    'right': [SDLK_RIGHT],
                    'jump':  [SDLK_KP_1],
                    'attack':[SDLK_KP_2],
                    'spear_attack': [SDLK_KP_5],
                    'parry': [SDLK_KP_3],
                }
        else:
            self.keymap = keymap


        # 플레이어별 라벨 색
        self.tag_color = (255, 255, 0) if self.pid == 1 else (0, 255, 255)


        self.next_idle_flip = get_time() + 0.125  # idle을 넘기는 기준의 시간이 되어주는

        self.shield_image = load_image('real_shield.png')  # 방패를
        
        #애니메이션을 위한 변수들
        self.anim_frame = 0
        self.idle_timer = 0.0

        #move를 위한 변수들
        self.move_frame = 0
        self.next_move_flip = get_time() + 0.125 # move를 넘기는 기준의 시간이 되어주는

        #jump를 위한 변수들
        self.jump_frame = 0
        self.next_jump_flip = get_time() + 0.1

        #attack를 위한 변수들
        self.attack_frame = 0
        self.next_attack_flip = get_time() + (1.0 / 15.0)

        # 방향, move 말고도 jump도 해당 방향으로 뛰고 공격도 해당 방향으로 하니까 여기에서 만들고 다룸.
        #self.face_dir = +1
        self.move_dir = 0  # -1: 왼쪽, 0: 안 움직임, +1: 오른쪽



        # 물리
        self.vx = 0.0
        self.vy = 0.0
        self.move_speed = 250.0     # px/s
        self.jump_speed = 1200.0    # px/s 위로
        self.gravity = -1200.0      # px/s^2
        self.max_jump_hold = 0.3    # 버튼 홀드로 더 올라갈 수 있는 시간(초)

        # 버프용 기본값 백업
        self.base_move_speed = self.move_speed
        self.base_jump_speed = self.jump_speed
        self.base_gravity = self.gravity

        #  공격 차지 시간(아이템으로 줄어드는 값)
        self.attack_charge_time = 3.0
        self.base_attack_charge_time = 3.0

        #  버프 종료 시각(없으면 0.0)
        self.speed_buff_until = 0.0
        self.attack_buff_until = 0.0
        self.jump_pressed_time = 0.0   # 언제 점프 시작했는지
        self.last_time = get_time()    # dt 구하려고

        self.action = "idle"

        #테스트용
        self.draw_w = 80
        self.draw_h = 80
        # 캔버스 크기 받아두기
        self.canvas_h = get_canvas_height()

        # 지금은 스테이지가 없으니까, 그냥 창을 그거로 한다.
        self.ground_y = 90   # 200이면 100


        self.weapon = None
        self.equipped = None
        self.attachments = []   # 나중에 검 말고 다른것도 할 예정이니까 이걸로 관리

        self.is_spear_attack_reserved = False
        self.spear_attack_time = None

        self.canvas_w = get_canvas_width()  # 상단 타이머 UI 위치 계산용
        self.weapon_pick_time = 0.0  # 무기 집은 시각
        self.weapon_time_limit = 30.0  # 제한 시간(초)

#타이머 표시를 위해 폰트 업로드
        self.font = None
        try:
            self.font = load_font('ENCR10B.TTF', 18)  # 프로젝트 루트에 TTF 파일 두기
        except:
            self.font = None  # 폰트 없을 때도 크래시 안나게


        # 시작 y도 이걸로 맞춰놓자
        self.x, self.y = 400, 150

        self.prev_x = self.x
        self.prev_y = self.y
        self.use_stage_collision = False
        self._eps = 0.8  # 여유폭

        #좌우 눌려있나 확인하는
        self.right_pressed = False
        self.left_pressed = False

        #j가 눌려있는지 아닌지
        self.is_jump_key_pressed = False

        # 앞으로 필요할 상태용(타이머 같은것도 일단 있음)
        self.is_attack_reserved = False
        self.attack_fire_time = None

        # 이 캐릭터가 "예약 공격을 실제로 발동될 수 있는 상태인지" 여부
        self.allow_reserved_attack = True

        self.signal_window_sec = 0.25
        self.parry_active_until = None
        self.parry_cooldown_until = None

        self.attack_cooldown_until = 0.0      # 평타(검) 쿨타임 끝나는 시각
        self.spear_cooldown_until = 0.0       # 창 던지기 쿨타임 끝나는 시각

        self.IDLE = Idle(self)
        self.MOVE = Move(self)
        self.JUMP_UP = Jump_Up(self)
        self.JUMP_FALL = Jump_Fall(self)
        self.JUMP_LAND = Jump_Land(self)
        self.ATTACK_FIRE = Attack_Fire(self)
        self.PARRY_HOLD = Parry_Hold(self)
        self.ATTACK_SPEAR = Attack_Spear(self)

        self._shield_pose = None  # 방패 위치/회전
        self._shield_obb = None # 방패 OBB
        self._shield_aabb = None

        self.state_machine = StateMachine(self.IDLE, {
            self.IDLE: {
                right_down: self.MOVE,
                left_down: self.MOVE,
                lambda e: right_up(e) and self.left_pressed: self.MOVE,
                lambda e: left_up(e) and self.right_pressed: self.MOVE,
                j_down: self.JUMP_UP,
                p_down: self.PARRY_HOLD,
                attack_ready: self.ATTACK_FIRE,
                attack_spear_ready: self.ATTACK_SPEAR
            },
            self.MOVE: {
                right_down: self.IDLE,
                left_down: self.IDLE,
                lambda e: right_up(e) and not self.left_pressed: self.IDLE,
                lambda e: left_up(e) and not self.right_pressed: self.IDLE,
        # 반대쪽이 눌려있으면 MOVE 유지
                lambda e: right_up(e) and self.left_pressed: self.MOVE,
                lambda e: left_up(e) and self.right_pressed: self.MOVE,
                j_down: self.JUMP_UP,
                attack_ready: self.ATTACK_FIRE,
                p_down: self.PARRY_HOLD,
                attack_spear_ready: self.ATTACK_SPEAR
            },
            # 위로 뜨는 중
            self.JUMP_UP: {
                # 키를 뗐거나 시간 끝나서 do()에서 'JUMP_FALL' 이벤트 던지면 여기로 감
                (lambda e: e[0] == 'JUMP_FALL'): self.JUMP_FALL,
                attack_ready: self.ATTACK_FIRE,
                attack_spear_ready: self.ATTACK_SPEAR

            },
            # 떨어지는 중
            self.JUMP_FALL: {
                # 착지하면 Character.update()나 Jump_Fall.do()에서 ('LAND', None) 던짐

                lambda e: e[0] == 'LAND': self.JUMP_LAND,
                attack_ready: self.ATTACK_FIRE,
                attack_spear_ready: self.ATTACK_SPEAR
            },
            # 착지 애니 돌기
            self.JUMP_LAND: {
                (lambda e, _self=self: e[0] == 'TIMEOUT' and (_self.right_pressed or _self.left_pressed)): self.MOVE,
                time_out: self.IDLE,
                # 네비게이션 등에서 강제로 이동 상태로 만들고 싶을 때
                (lambda e: e[0] == 'BREAK_TO_MOVE'): self.MOVE,
                # 착지 모션 중에도 점프 키를 다시 누르면 재점프 허용
                j_down: self.JUMP_UP,
                attack_ready: self.ATTACK_FIRE,
                attack_spear_ready: self.ATTACK_SPEAR
            },
            self.ATTACK_FIRE: {
                attack_end_air: self.JUMP_FALL,  # 착지 모션/낙하 상태로 (JumpLand 쓰면 그걸로 교체)
                attack_end_move: self.MOVE,
                attack_end_idle: self.IDLE,
                (lambda e: e[0] == 'BREAK_TO_MOVE'): self.MOVE,
            },
            self.PARRY_HOLD: {
                p_up: self.IDLE,
                right_down: self.MOVE,
                left_down: self.MOVE,
                (lambda e: e[0] == 'PARRY_EXPIRE'): self.IDLE,
                (lambda e: e[0] == 'BREAK_TO_MOVE'): self.MOVE

            },
            self.ATTACK_SPEAR: {
                attack_end_air: self.JUMP_FALL,
                attack_end_move: self.MOVE,
                attack_end_idle: self.IDLE,
                (lambda e: e[0] == 'BREAK_TO_MOVE'): self.MOVE,
            }
        })
        pass

    def handle_event(self, event):

        # 1) 내 키가 아니면 무시
        if event.type in (SDL_KEYDOWN, SDL_KEYUP):
            if not self._belongs_to_me(event.key):
                return

            # 2) 공용 키로 정규화
            vk = self._normalize_key(event.key)
            if vk is None:
                return
            event = SimpleNamespace(type=event.type, key=vk)


        # --- 좌/우 눌림 상태 관리 ---
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_RIGHT:
                self.right_pressed = True
            elif event.key == SDLK_LEFT:
                self.left_pressed = True
        elif event.type == SDL_KEYUP:
            if event.key == SDLK_RIGHT:
                self.right_pressed = False
            elif event.key == SDLK_LEFT:
                self.left_pressed = False

        # 점프키 플래그/낙하 전환 (기존 유지)
        if event.type == SDL_KEYDOWN and event.key == SDLK_j:
            self.is_jump_key_pressed = True
        elif event.type == SDL_KEYUP and event.key == SDLK_j:
            self.is_jump_key_pressed = False
            self.state_machine.handle_state_event(('JUMP_FALL', None))

#창 말고도 그냥 검에도 하게

        if event.type == SDL_KEYDOWN and event.key == SDLK_p:
            now = get_time()

            # 이미 패링 상태면(유지시간 안에서) 다시 누르기 금지
            if self.state_machine.cur_state is self.PARRY_HOLD:
                return

            # 쿨타임 중이면 시작 불가
            if self.parry_cooldown_until and now < self.parry_cooldown_until:
                return

        # 공격: 즉시 전이 X, 예약만 걸고 반환
        # 공격: 즉시 전이 X, 예약만 걸고 반환
        if event.type == SDL_KEYDOWN and event.key == SDLK_k:
            now = get_time()

            if now < self.attack_cooldown_until:
                return

            if self.weapon is None:
                return

            if not self.is_attack_reserved:
                self.is_attack_reserved = True
                self.attack_fire_time = now + self.attack_charge_time
                # 여기서 1~2초 정도 락 걸면 됨. 네가 원하는 값으로 조절해.
                self.attack_cooldown_until = now + 1.2  # 예: 1.2초
            return  # 공격은 상태머신에 바로 전달하지 않음

        if event.type == SDL_KEYDOWN and event.key == SDLK_i:  # 창 던지기
            now = get_time()

            # 쿨타임 중이면 무시
            if now < self.spear_cooldown_until:
                return

            # 무기 없으면 창 공격 예약 X
            if self.weapon is None:
                return

            if not self.is_spear_attack_reserved:
                self.is_spear_attack_reserved = True
                self.spear_attack_time = now + self.attack_charge_time
                self.spear_cooldown_until = now + 1.2
            return  # 창 공격도 즉시 상태 전이 안 함

        # 나머지는 상태머신에 그대로 전달
        self.state_machine.handle_state_event(('INPUT', event))

    def _belongs_to_me(self, key):# 이게 1p용 키인지 2p용 키인지 확인하는 함수로
        for keys in self.keymap.values():
            if key in keys:
                return True
        return False

    def _normalize_key(self, key): #키를 표준화 시켜주는
        if key in self.keymap['left']:   return SDLK_LEFT
        if key in self.keymap['right']:  return SDLK_RIGHT
        if key in self.keymap['jump']:   return SDLK_j
        if key in self.keymap['attack']: return SDLK_k
        if 'spear_attack' in self.keymap and key in self.keymap['spear_attack']: return SDLK_i
        if key in self.keymap['parry']:  return SDLK_p
        return None
        
    def update(self):
        # 생각해봤는데 상태랑 상관없이 무조건 매 프레임 돌아야 하는 애들은 그냥 한번에 여기서 계산하기로 하는게 편하지 않을까?
        now = get_time()

        # 패링 유효창(저스트) 갱신
        self.parry_active = (self.parry_active_until is not None and now <= self.parry_active_until)

        # 버프 만료 체크
        if self.speed_buff_until and now > self.speed_buff_until:
            self.speed_buff_until = 0.0
            self.move_speed = self.base_move_speed
            self.jump_speed = self.base_jump_speed
            self.gravity = self.base_gravity

        if self.attack_buff_until and now > self.attack_buff_until:
            self.attack_buff_until = 0.0
            self.attack_charge_time = self.base_attack_charge_time

        # 이전 위치 저장
        self.prev_x, self.prev_y = self.x, self.y

        # 공격 예약(차지) 도달 체크
        if self.is_attack_reserved and self.attack_fire_time is not None:
            # 0) AI가 이 프레임에 예약 공격을 막아놨으면 그냥 취소하고 끝
            if not getattr(self, 'allow_reserved_attack', True):
                self.is_attack_reserved = False
                self.attack_fire_time = None

            # 1) 무기가 없으면 예약만 취소하고 끝
            elif self.weapon is None:
                self.is_attack_reserved = False
                self.attack_fire_time = None

            # 2) 무기가 있을 때만 ATTACK_READY 발동
            elif now >= self.attack_fire_time:
                self.is_attack_reserved = False
                self.attack_fire_time = None
                air = self.y > self.ground_y
                self.state_machine.handle_state_event(('ATTACK_READY', {'air': air}))

        if self.is_spear_attack_reserved and self.spear_attack_time is not None:
            if now >= self.spear_attack_time:
                self.is_spear_attack_reserved = False
                self.spear_attack_time = None
                air = self.y > self.ground_y
                self.state_machine.handle_state_event(('ATTACK_SPEAR_READY', {'air': air}))

        now = get_time()
        dt = game_framework.frame_time
        self.last_time = now

        if self.weapon:
            if not self.weapon_pick_time:
                self.weapon_pick_time = now
            if now - self.weapon_pick_time >= self.weapon_time_limit:
                w = self.weapon
                if hasattr(w, 'reset_to_ground_random'):
                    w.reset_to_ground_random()  # 패링 튕김과 동일한 효과
                self.weapon = None
                self.weapon_pick_time = 0.0
        else:
            # 들고 있지 않으면 타이머 초기화
            self.weapon_pick_time = 0.0


        r = 1 if self.right_pressed else 0
        l = 1 if self.left_pressed else 0
        if r and not l:
            self.move_dir = +1
        elif l and not r:
            self.move_dir = -1
        elif r and l:  # 동시 입력일 때 정책: "마지막으로 누른 방향" 우선
            # 마지막 누른 방향을 기억하고 싶다면 아래 3줄 추가:
            # (필드) self.last_dir_pressed = +1/-1  를 __init__에 0으로 초기화
            # (handle_event에서) KEYDOWN 시 self.last_dir_pressed = +1 또는 -1 갱신
            self.move_dir = self.last_dir_pressed if hasattr(self, 'last_dir_pressed') and self.last_dir_pressed else 0
        else:
            self.move_dir = 0

        # 얼굴 방향은 어느 상태든 움직임이 있으면 그쪽으로
        if self.move_dir != 0:
            self.face_dir = 1 if self.move_dir > 0 else -1

        # 가로 이동
        self.vx = self.move_speed * self.move_dir
        self.x += self.vx * dt

        # 세로 이동
        self.vy += self.gravity * dt
        self.y += self.vy * dt

        # 바닥
        if not getattr(self, 'use_stage_collision', False):
            if self.y <= self.ground_y:
                self.y = self.ground_y
                self.vy = 0
                if self.state_machine.cur_state in (self.JUMP_UP, self.JUMP_FALL):
                    self.state_machine.handle_state_event(('LAND', None))

        self.state_machine.update()

        if getattr(self, 'action', None) == 'parry_hold':
            cur = self._current_frame_info() if hasattr(self, '_current_frame_info') else None
            if cur:
                act, idx, wh = cur
                fw, fh = wh if isinstance(wh, (tuple, list)) and len(wh) == 2 else (self.draw_w, self.draw_h)

                ox_src, oy_src = 21.47, 9.07
                deg = 0.0


                sx = self.draw_w / float(max(fw, 1))
                sy = self.draw_h / float(max(fh, 1))

                hy = self.y - self.draw_h * 0.5 + oy_src * sy
                if self.face_dir == 1:
                    hx = self.x - self.draw_w * 0.5 + ox_src * sx
                    deg_prime, flip = deg, ''
                else:
                    hx = self.x + self.draw_w * 0.5 - ox_src * sx
                    deg_prime, flip = 180.0 - deg, 'h'

                img = self.shield_image
                sw, sh = img.w, img.h
                scale = self.draw_h / 30.0
                dw, dh = int(sw * scale), int(sh * scale)
                rad = math.radians(deg_prime)

                self._shield_pose = (hx, hy, rad, flip, dw, dh)

                hw, hh = dw * 0.5, dh * 0.5
                c, s = math.cos(rad), math.sin(rad)
                self._shield_obb = (
                    (hx + (+hw) * c - (+hh) * s, hy + (+hw) * s + (+hh) * c),
                    (hx + (+hw) * c - (-hh) * s, hy + (+hw) * s + (-hh) * c),
                    (hx + (-hw) * c - (-hh) * s, hy + (-hw) * s + (-hh) * c),
                    (hx + (-hw) * c - (+hh) * s, hy + (-hw) * s + (+hh) * c),
                )

                xs = [p[0] for p in self._shield_obb]
                ys = [p[1] for p in self._shield_obb]
                self._shield_aabb = (min(xs), min(ys), max(xs), max(ys))

    def _reservation_info(self):
        # spear 우선(동시에 걸릴 상황은 없게 설계했지만 안전하게)
        if self.is_spear_attack_reserved and self.spear_attack_time:
            return True, self.spear_attack_time, self.attack_charge_time
        if self.is_attack_reserved and self.attack_fire_time:
            return True, self.attack_fire_time, self.attack_charge_time
        return False, None, None

    def draw(self):
        self.state_machine.draw()
        self._draw_shield_if_parry()
        self.draw_sweat_overlay()
        #draw_rectangle(*self.get_bb())

        # 머리 위 작은 박스(기존 위치 유지)
        hx1, hy1 = self.x - 8, self.y + self.draw_h // 2 + 18
        hx2, hy2 = self.x + 8, self.y + self.draw_h // 2 + 30
        #draw_rectangle(hx1, hy1, hx2, hy2)

        if self.weapon and self.weapon_pick_time and self.font:
            now = get_time()
            remain = max(0.0, self.weapon_time_limit - (now - self.weapon_pick_time))
            label = f"{remain:0.1f}s"
            # 대충 중앙 정렬 느낌으로 약간 왼쪽 보정
            tx = (hx1 + hx2) * 0.5 - 12
            ty = hy2 + 2
            self.font.draw(tx, ty, label, (255, 255, 255))

    def draw_sweat_overlay(self):
        active, fire_time, total = self._reservation_info()
        if not active:
            return
        now = get_time()
        t_rem = fire_time - now
        if t_rem <= 0:
            return

        progress = 1.0 - (t_rem / total)
        progress = max(0.0, min(1.0, progress))

        # 현재 애니 프레임 키/인덱스 계산 (기존 로직 그대로)
        action = self.action
        if action in ('jump_up', 'jump_fall'):
            idx, action_key = self.jump_frame, 'jump_land'
        elif action == 'idle':
            idx, action_key = self.anim_frame, 'idle'
        elif action == 'move':
            idx, action_key = self.move_frame, 'move'
        elif action == 'attack_fire':
            idx, action_key = self.attack_frame, 'attack_fire'
        elif action == 'attack_spear':
            idx, action_key = self.attack_frame, 'attack_spear'
        elif action == 'parry_hold':
            idx, action_key = 0, 'parry_hold'
        else:
            idx, action_key = self.jump_frame, 'jump_land'

        l, b, w, h = sprite[ACTION[action_key]][idx]
        sx_scale = self.draw_w / max(w, 1)
        sy_scale = self.draw_h / max(h, 1)

        ox = (self.draw_w * 0.35) * (1 if self.face_dir == 1 else -1)
        oy = (self.draw_h * 0.35)
        fall_px = int(self.draw_h * 0.25 * progress)
        sx = self.x + ox
        sy = self.y + oy - fall_px

        sl, sb, sw, sh = sweat[0]
        sdw = int(sw * sx_scale)
        sdh = int(sh * sy_scale)

        self.image.clip_draw(sl, sb, sw, sh, sx, sy, sdw, sdh)

    def get_bb(self):
            halfw = self.draw_w // 2 -8
            halfh = self.draw_h // 2-8
            return self.x - halfw, self.y - halfh, self.x + halfw, self.y + halfh

    def pickup_spear(self, other):
        if self.weapon: return
        self.weapon = other
        game_world.remove_collision_object_once(other, 'char:spear')
        other.attach_to(self)
        other.state = 'EQUIPPED'
        return

    def handle_collision(self, group, other):
        if group == 'char:sword' and self.weapon is None and getattr(other, 'state', '') == 'GROUND':
            self.pickup_sword(other)
            return
        if group == 'char:stage':
            self._solve_stage_collision(other)  # other = StageColliders
            return
        if group == 'char:item':
            if hasattr(other, 'apply_to'):
                other.apply_to(self)
            return

        if group == 'attack_sword:char':
            sword = other

            #  이미 파링으로 비활성화된 칼은 무시(동일 프레임 재충돌 방지)
            if getattr(sword, '_parry_lock', False):
                return

            #  자기 칼이면 무시
            if getattr(sword, 'owner', None) is self:
                return

            # 파링 중이면 칼을 튕김
            if getattr(self, 'action', '') == 'parry_hold' or getattr(self, 'parry_active', False):

                try:
                    # 다음 충돌 루프에서 이 칼은 공격 판정에서 제외되도록 락을 건다
                    sword._parry_lock = True
                    sword.reset_to_ground_random()
                finally:
                    #import game_world
                    game_world.remove_collision_object_once(sword, 'attack_sword:char')
                return

            #  진짜 공격 칼인지 찐 확인(프레임 중간에 상태가 바뀌었을 수 있음)
            is_active_attack = (
                    getattr(sword, 'state', '') == 'EQUIPPED'
                    and getattr(sword, 'owner', None) is not None
                    and getattr(sword.owner, 'action', '') == 'attack_fire'
            )
            if not is_active_attack:
                return

            # 4) 여기까지 왔다면 즉사(월드에서 제거)
            #import game_world
            game_world.remove_object(self)
            return

        if group == 'char:spear':
            from spear import Spear

            # other 가 Spear 이고, 땅에 박힌 상태 + 아무 무기도 안 들고 있을 때만 줍기
            if isinstance(other, Spear):
                spear = other
                if spear.state == 'GROUND' and self.weapon is None:
                    spear.attach_to(self)
                    self.weapon = spear
            return

        if group == 'attack_spear:char':
            from spear import Spear

            if not isinstance(other, Spear):
                return

            spear = other

            # 1) 자기 자신이 던진 창이면 충돌 무시
            #    → 던지는 순간 자기 몸에 닿아서 바로 꽃히는 버그 방지
            if spear.owner is self:
                return

            # 2) 패링 활성 상태면 창 튕기고 끝
            if getattr(self, 'parry_active', False):
                spear.reset_to_ground_random()
                return

            # 3) 그 외엔 피격 처리 (지금은 그냥 캐릭터 삭제)
            game_world.remove_collision_object_once(spear, 'attack_spear:char')
            game_world.remove_object(self)
            return

    def pickup_sword(self, sword):
        # 이미 무기 들고 있으면 무시
        if getattr(self, 'weapon', None):
            return

        # 이 캐릭터가 해당 검을 장비
        self.weapon = sword
        sword.state = 'EQUIPPED'
        sword.owner = self

        # 검을 캐릭터에 붙이는 기존 헬퍼가 있으면 사용
        if hasattr(sword, 'attach_to'):
            sword.attach_to(self)

        # 공격 사거리 같은 게 있으면 검 길이에 맞게 갱신
        if hasattr(self, 'attack_range') and hasattr(sword, 'length'):
            self.attack_range = sword.length

    def _current_frame_info(self):
        act = self.action  # 'idle','move','attack_fire','parry_hold','jump_up','jump_fall','jump_land'
        if act == 'idle':
            idx = self.anim_frame
            key = 'idle'
        elif act == 'move':
            idx = self.move_frame
            key = 'move'
        elif act == 'attack_fire':
            idx = self.attack_frame
            key = 'attack_fire'
        elif act == 'parry_hold':
            idx = 0
            key = 'parry_hold'
        elif act in ('jump_up', 'jump_fall', 'jump_land'):
            idx = self.jump_frame
            key = 'jump_land'  # ← 점프 계열은 시트 키 통일
        elif act == 'attack_spear':
            idx = self.attack_frame
            key = 'attack_spear'
        else:
            return None

        l, b, w, h = sprite[ACTION[key]][idx]
        return key, idx, (w, h)



    def _draw_shield_if_parry(self):

        if getattr(self, 'action', None) != 'parry_hold':
            return
        if not self._shield_pose:
            return

        hx, hy, rad, flip, dw, dh = self._shield_pose
        img = self.shield_image

        img.clip_composite_draw(0, 0, img.w, img.h, rad, flip, hx, hy, dw, dh)

        if self._shield_aabb:
            l, b, r, t = self._shield_aabb
            #draw_rectangle(l, b, r, t)

        if self._shield_obb:
            for i in range(4):
                x1, y1 = self._shield_obb[i]
                x2, y2 = self._shield_obb[(i + 1) % 4]
                #draw_line(x1, y1, x2, y2)

    def get_obb(self):
        # 패링 중이면 방패 OBB만 충돌 대상으로 사용
        if getattr(self, 'action', None) == 'parry_hold' and self._shield_obb:
            return self._shield_obb
        # 아니면 몸통 AABB의 네 꼭짓점을 반환(기존 충돌 동작 유지)
        l, b, r, t = self.get_bb()
        return ((l, b), (r, b), (r, t), (l, t))

    def _aabb_intersect(self, a, b):
        al, ab, ar, at = a;
        bl, bb, br, bt = b
        return not (ar <= bl or al >= br or at <= bb or ab >= bt)

    def _half_extents(self):
        halfw = self.draw_w // 2 - 8
        halfh = self.draw_h // 2 - 8
        return halfw, halfh


    def _solve_stage_collision(self, stage):
        cur_bb = self.get_bb()
        near = stage.query_boxes(cur_bb, margin=2.0)

        if not near:
            return

        hw, hh = self._half_extents()
        prev_bb = (self.prev_x - hw, self.prev_y - hh, self.prev_x + hw, self.prev_y + hh)

        landed_top = None
        hit_bottom = None

        if self.vy <= 0:
            for _, typ, L, B, R, T in near:
                if not self._aabb_intersect(cur_bb, (L, B, R, T)): continue
                if prev_bb[1] >= T and cur_bb[1] < T + self._eps:
                    if landed_top is None or T > landed_top:
                        landed_top = T
            if landed_top is not None:
                self.y = landed_top + hh
                self.vy = 0
                cur_bb = self.get_bb()
                if self.state_machine.cur_state in (self.JUMP_UP, self.JUMP_FALL):
                    self.state_machine.handle_state_event(('LAND', None))

        elif self.vy > 0:
            for _, typ, L, B, R, T in near:
                if not self._aabb_intersect(cur_bb, (L, B, R, T)): continue
                if prev_bb[3] <= B and cur_bb[3] > B - self._eps:
                    if hit_bottom is None or B < hit_bottom:
                        hit_bottom = B
            if hit_bottom is not None:
                self.y = hit_bottom - hh
                self.vy = 0
                cur_bb = self.get_bb()

        push_left = None
        push_right = None

        if self.vx > 0:
            for _, typ, L, B, R, T in near:
                if not self._aabb_intersect(cur_bb, (L, B, R, T)): continue
                if prev_bb[2] <= L and cur_bb[2] > L - self._eps:
                    if push_left is None or L < push_left:
                        push_left = L
            if push_left is not None:
                self.x = push_left - hw
                self.vx = 0
                cur_bb = self.get_bb()

        elif self.vx < 0:
            for _, typ, L, B, R, T in near:
                if not self._aabb_intersect(cur_bb, (L, B, R, T)): continue
                if prev_bb[0] >= R and cur_bb[0] < R + self._eps:
                    if push_right is None or R > push_right:
                        push_right = R
            if push_right is not None:
                self.x = push_right + hw
                self.vx = 0
                cur_bb = self.get_bb()
