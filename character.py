from types import SimpleNamespace

from pico2d import load_image, get_time, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_RIGHT, SDLK_LEFT, SDLK_a, \
    get_canvas_height, draw_rectangle, load_font, draw_line
from sdl2 import SDLK_j, SDLK_p, SDLK_k

import os

from pico2d import (SDL_KEYDOWN, SDL_KEYUP,
                    SDLK_LEFT, SDLK_RIGHT, SDLK_j, SDLK_k, SDLK_p,
                    SDLK_a, SDLK_d, SDLK_KP_1, SDLK_KP_2, SDLK_KP_3) # 2p키까지 감안해서 그냥 한번에 해버리기
# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine
import math
import game_world
from sword_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX


# 공격의 여러 상태를 추가(이게 공격 이후 어떤상태에 갈지도 다 다르기 떄무네)
def attack_ready(e):      return e[0] == 'ATTACK_READY'
def attack_end_air(e):   return e[0] == 'ATTACK_END_AIR'
def attack_end_move(e):   return e[0] == 'ATTACK_END_MOVE'
def attack_end_idle(e):   return e[0] == 'ATTACK_END_IDLE'

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




class Idle:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "idle"
        self.boy.move_dir = 0

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):

        now = get_time()

        while now >= self.boy.next_idle_flip:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)


class Move:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "move"


    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):

        now = get_time()

        STEP = 0.125
        while now >= self.boy.next_move_flip:
            self.boy.move_frame = (self.boy.move_frame + 1) % 10  # 0~9
            self.boy.next_move_flip += STEP

        l, b, w, h = sprite[ACTION['move']][self.boy.move_frame]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)


class Jump_Up:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_up"
        self.boy.jump_frame = 0
        self.boy.vy = self.boy.jump_speed
        self.boy.jump_pressed_time = get_time()


    def exit(self, event):
        pass

    def do(self):
        # 점프 키를 뗐거나, 홀드 시간이 끝났으면 떨어지는 상태로 넘김(마리오 보면 점프키 때기 전까지 계속 위로 올라가니까)
        now = get_time()
        if (not self.boy.is_jump_key_pressed) or (now - self.boy.jump_pressed_time > self.boy.max_jump_hold):
            self.boy.state_machine.handle_state_event(('JUMP_FALL', None))

    def draw(self):
        # 프레임 0만 그린다
        l, b, w, h = sprite[ACTION['jump_land']][0]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)


class Jump_Fall:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_fall"
        self.boy.jump_frame = 1
        # 혹시 위로 너무 천천히 가고 있으면 아래로 방향만 만들기
        if self.boy.vy > 0:
            self.boy.vy = 0


    def exit(self, event):
        pass

    def do(self):
        # 여기서는 그냥 떨어지기만 한다.
        # 땅 닿으면 착지 이벤트로 넘겨주는거임
        if self.boy.y <= self.boy.ground_y:
            self.boy.y = self.boy.ground_y
            self.boy.vy = 0
            self.boy.state_machine.handle_state_event(('LAND', None))

    def draw(self):
        l, b, w, h = sprite[ACTION['jump_land']][1]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        #이것도 내려오는 이미지가 1개로 그냥 이것만 보여주는거임

class Jump_Land:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_land"
        self.boy.jump_frame = 0
        STEP = 0.05  # draw의 STEP과 동일하게
        self.boy.next_jump_flip = get_time() + STEP


    def exit(self, event):

        if 2 <= self.boy.jump_frame <= 7:
            now = get_time()
            dt = now - self._last_time
            self._last_time = now
            self.boy.x += self.boy.face_dir * self._roll_speed * dt

    def do(self):
        pass

    def draw(self):
        now = get_time()
        STEP = 0.05
        while now >= self.boy.next_jump_flip and self.boy.jump_frame < 9:
            self.boy.jump_frame += 1
            self.boy.next_jump_flip += STEP

        l, b, w, h = sprite[ACTION['jump_land']][self.boy.jump_frame]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)

        if self.boy.jump_frame == 9:
            self.boy.state_machine.handle_state_event(('TIMEOUT', None))

class Attack_Fire:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, ev=None):
        # 애니 초기화
        self.boy.action = "attack_fire"
        self.boy.attack_frame = 0
        self._step = 1.0 / 15.0   # ~15fps
        #self._step = 0.9  # ~15fps
        self._next = get_time() + self._step
        # 발동 순간의 공중 여부와 Y위치 저장해놓기
        self._from_air = bool(ev and isinstance(ev, tuple) and ev[1] and ev[1].get('air'))
        self._anchor_y = self.boy.y

    def exit(self, ev=None):
        pass

    def do(self):
        pass  # 시간 진행은 draw에서

    def draw(self):
        now = get_time()

        # 위치 잠금(공중/지상 모두 공격 중엔 Y를 고정)
        self.boy.y = self._anchor_y

        # 프레임 진행
        while now >= self._next and self.boy.attack_frame < 7:
            self.boy.attack_frame += 1
            self._next += self._step

        # 렌더
        l, b, w, h = sprite[ACTION['attack_fire']][self.boy.attack_frame]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)

        if self.boy.attack_frame >= 6:  # 마지막 프레임
            if self._from_air:
                self.boy.state_machine.handle_state_event(('ATTACK_END_AIR', None))
            else:
                if self.boy.right_pressed or self.boy.left_pressed:
                    self.boy.state_machine.handle_state_event(('ATTACK_END_MOVE', None))
                else:
                    self.boy.state_machine.handle_state_event(('ATTACK_END_IDLE', None))

class Parry_Hold:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "parry_hold"

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):
        # parry_hold는 1프레임 고정
        l, b, w, h = sprite[ACTION['parry_hold']][0]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)


class Character:
    def __init__(self, pid=1, keymap=None):
        self.x, self.y = 400, 150 # 이건 그냥 띄워보려는 거니까 일단 임의위치 위에 띄우려는
        self.pid = pid
        #self.font = load_font('ENCR10B.TTF', 16)
        self.move_dir = 0
        self.image = load_image('project_character_sheet.png')

        if keymap is None:
            if pid == 1:
                self.face_dir = +1
                self.keymap = {
                    'left':  [SDLK_a],
                    'right': [SDLK_d],
                    'jump':  [SDLK_j],
                    'attack':[SDLK_k],
                    'parry': [SDLK_p],
                }
            else:  # pid == 2
                self.face_dir = -1
                self.keymap = {

                    'left':  [SDLK_LEFT],
                    'right': [SDLK_RIGHT],
                    'jump':  [SDLK_KP_1],
                    'attack':[SDLK_KP_2],
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
        self.jump_speed = 700.0     # px/s 위로
        self.gravity = -1500.0      # px/s^2
        self.max_jump_hold = 0.18   # 버튼 홀드로 더 올라갈 수 있는 시간(초)

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


        # 시작 y도 이걸로 맞춰놓자
        self.x, self.y = 400, 150

        #좌우 눌려있나 확인하는
        self.right_pressed = False
        self.left_pressed = False

        #j가 눌려있는지 아닌지
        self.is_jump_key_pressed = False

        # 앞으로 필요할 상태용(타이머 같은것도 일단 있음)
        self.is_attack_reserved = False
        self.attack_fire_time = None

        self.signal_window_sec = 0.25
        self.parry_active_until = None
        self.parry_cooldown_until = None

        self.IDLE = Idle(self)
        self.MOVE = Move(self)
        self.JUMP_UP = Jump_Up(self)
        self.JUMP_FALL = Jump_Fall(self)
        self.JUMP_LAND = Jump_Land(self)
        self.ATTACK_FIRE = Attack_Fire(self)
        self.PARRY_HOLD = Parry_Hold(self)

        self._shield_pose = None  # 방패 위치/회전
        self._shield_obb = None # 방패 OBB
        self._shield_aabb = None

        self.state_machine = StateMachine(self.IDLE, {
            self.IDLE: {
                right_down: self.MOVE,
                left_down: self.MOVE,
                right_up: self.MOVE,
                left_up: self.MOVE,
                j_down: self.JUMP_UP,
                p_down: self.PARRY_HOLD,
                attack_ready: self.ATTACK_FIRE
            },
            self.MOVE: {
                right_down: self.IDLE,
                left_down: self.IDLE,
                right_up: self.IDLE,
                left_up: self.IDLE,
                j_down: self.JUMP_UP,
                attack_ready: self.ATTACK_FIRE,
                p_down: self.PARRY_HOLD,
            },
            # 위로 뜨는 중
            self.JUMP_UP: {
                # 키를 뗐거나 시간 끝나서 do()에서 'JUMP_FALL' 이벤트 던지면 여기로 감
                (lambda e: e[0] == 'JUMP_FALL'): self.JUMP_FALL,
                attack_ready: self.ATTACK_FIRE

            },
            # 떨어지는 중
            self.JUMP_FALL: {
                # 착지하면 Character.update()나 Jump_Fall.do()에서 ('LAND', None) 던짐

                lambda e: e[0] == 'LAND': self.JUMP_LAND,
                attack_ready: self.ATTACK_FIRE
            },
            # 착지 애니 돌기
            self.JUMP_LAND: {
                (lambda e, _self=self: e[0] == 'TIMEOUT' and (_self.right_pressed or _self.left_pressed)): self.MOVE,
                time_out: self.IDLE
            },
            self.ATTACK_FIRE: {
                attack_end_air: self.JUMP_FALL,  # 착지 모션/낙하 상태로 (JumpLand 쓰면 그걸로 교체)
                attack_end_move: self.MOVE,
                attack_end_idle: self.IDLE,
            },
            self.PARRY_HOLD: {
                p_up: self.IDLE,
                right_down: self.MOVE,
                left_down: self.MOVE

            },
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

        # 공격: 즉시 전이 X, 예약만 걸고 반환
        if event.type == SDL_KEYDOWN and event.key == SDLK_k:
            if not self.is_attack_reserved:
                self.is_attack_reserved = True
                self.attack_fire_time = get_time() + 3.0  # 3초 뒤 발동
            return  # 공격은 상태머신에 바로 전달하지 않음

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
        if key in self.keymap['parry']:  return SDLK_p
        return None
        
    def update(self):
        #생각해봤는데 상태랑 상관없이 무조건 매 프레임 돌아야 하는 애들은 그냥 한번에 여기서 계산하기로 하는게 편하지 않을까?

        # 3초 예약 도달 체크
        if self.is_attack_reserved and self.attack_fire_time is not None:
            now = get_time()
            if now >= self.attack_fire_time:
                self.is_attack_reserved = False
                self.attack_fire_time = None
                # 공중/지상 판단
                air = getattr(self, 'y', 0) > getattr(self, 'ground_y', 0)
                self.state_machine.handle_state_event(('ATTACK_READY', {'air': air}))


        now = get_time()
        dt = now - self.last_time
        self.last_time = now

        # --- 좌/우 입력 해석 ---
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
        if self.y <= self.ground_y:
            self.y = self.ground_y
            self.vy = 0
            # 공중 상태일 때만 LAND 보내기
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


    def draw(self):
        self.state_machine.draw()
       # self._draw_weapon_if_any()# 무기 그려야지
        self._draw_shield_if_parry()
        self.draw_sweat_overlay() # 캐릭터 관련된걸 그리고 그 위에 땀방울을 그리는
        draw_rectangle(*self.get_bb())

        c1 = (255, 255, 0) if self.pid == 1 else (0, 255, 255)
        hx1, hy1 = self.x - 8, self.y + self.draw_h // 2 + 18
        hx2, hy2 = self.x + 8, self.y + self.draw_h // 2 + 30
        draw_rectangle(hx1, hy1, hx2, hy2)

    def draw_sweat_overlay(self):
        # 예약 중이 아니면 표시 안 함
        if not (self.is_attack_reserved and self.attack_fire_time is not None):
            return

        now = get_time()
        t_rem = self.attack_fire_time - now
        if t_rem <= 0:
            return

        # 진행도(0→1)
        T_TOTAL = 3.0
        progress = 1.0 - (t_rem / T_TOTAL)
        if progress < 0.0: progress = 0.0
        if progress > 1.0: progress = 1.0

        # 마지막 신호창(0.25s)에서 깜빡임
        if t_rem <= getattr(self, 'signal_window_sec', 0.25):
            if int(now * 16) % 2 == 1:
                return

        # 현재 프레임의 원본 크기(w,h) → 몸체 스케일 비율 계산
        action = self.action  # 'idle','move','jump_land','attack_fire','parry_hold'
        if action == 'idle':
            idx = self.anim_frame
        elif action == 'move':
            idx = self.move_frame
        elif action == 'attack_fire':
            idx = self.attack_frame
        elif action == 'parry_hold':
            idx = 0
        else:  # 'jump_land' 등
            idx = self.jump_frame

        l, b, w, h = sprite[ACTION[action]][idx]
        # 몸체가 (w,h) → (draw_w,draw_h)로 그려지므로 이 비율을 따라간다
        sx_scale = self.draw_w / max(w, 1)
        sy_scale = self.draw_h / max(h, 1)

        # 머리 옆 기준 오프셋(스케일 반영)
        ox = (self.draw_w * 0.35) * (1 if self.face_dir == 1 else -1)
        oy = (self.draw_h * 0.35)

        # 진행도에 따른 하강(스케일 반영)
        fall_px = int(self.draw_h * 0.25 * progress)

        sx = self.x + ox
        sy = self.y + oy - fall_px

        # sweat[0] 조각을 몸체와 같은 비율로 스케일
        sl, sb, sw, sh = sweat[0]
        sdw = int(sw * sx_scale)
        sdh = int(sh * sy_scale)

        # 땀방울은 좌우 반전 없이 위치만 반대로 (대칭 이미지)
        self.image.clip_draw(sl, sb, sw, sh, sx, sy, sdw, sdh)

    def get_bb(self):
            halfw = self.draw_w // 2
            halfh = self.draw_h // 2
            return self.x - halfw, self.y - halfh, self.x + halfw, self.y + halfh

    def handle_collision(self, group, other):
        if group == 'char:sword' and self.weapon is None and getattr(other, 'state', '') == 'GROUND':
            self.pickup_sword(other)
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
                    import game_world
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
            import game_world
            game_world.remove_object(self)
            return

    def pickup_sword(self, other):
            if self.weapon:  # 이미 들고 있으면 무시
                return
            #sword.set_equipped()
            self.weapon = other
            game_world.remove_collision_object_once(other, 'char:sword')
            print('무기 장착 (월드 유지, EQUIPPED)')
            other.attach_to(self)
            other.state = 'EQUIPPED'
            return


    def _current_frame_info(self):
            act = self.action  # 'idle','move','attack_fire', ...
            if act == 'idle':
                idx = self.anim_frame
            elif act == 'move':
                idx = self.move_frame
            elif act == 'attack_fire':
                idx = self.attack_frame
            elif act == 'parry_hold':
                idx = 0
            else:
                return None
            l, b, w, h = sprite[ACTION[act]][idx]
            return act, idx, (w, h)

    def _draw_weapon_if_any(self):
        if not self.weapon:
            return

        if getattr(self, 'action', None) == 'parry_hold':
            return

        cur = self._current_frame_info()
        if not cur:
            return
        act, idx, (fw, fh) = cur


        lst = POSE.get(act)
        if not lst or idx >= len(lst):
            return
        pose = lst[idx]
        if not pose:
            return

        ox_src, oy_src = pose['offset_src_px']
        deg = pose['deg']


        sx = self.draw_w / float(fw)
        sy = self.draw_h / float(fh)


        if self.face_dir == 1:
            hx = self.x - self.draw_w * 0.5 + ox_src * sx
            deg_prime, flip = deg, ''
        else:
            hx = self.x + self.draw_w * 0.5 - ox_src * sx  # 좌우 미러
            if LEFT_FLIP_RULE == 'NEGATE':
                deg_prime, flip = -deg, 'h'
            elif LEFT_FLIP_RULE == 'KEEP':
                deg_prime, flip = deg, 'h'
            else:  # 'ADD_PI'
                deg_prime, flip = deg + 180.0, 'h'

        hy = self.y - self.draw_h * 0.5 + oy_src * sy


        img = self.weapon.image  # real_sword.png (15x31)
        sw, sh = img.w, img.h
        scale = self.draw_h / 50.0
        dw, dh = int(sw * scale), int(sh * scale)

        dx, dy = PIVOT_FROM_CENTER_PX  # 검 '센터'→'손잡이' 벡터(px)
        dx *= scale
        dy *= scale
        rad = math.radians(deg_prime)
        rx = dx * math.cos(rad) - dy * math.sin(rad)
        ry = dx * math.sin(rad) + dy * math.cos(rad)

        cx = hx + rx
        cy = hy + ry

        img.clip_composite_draw(0, 0, sw, sh, rad, flip, cx, cy, dw, dh)

        # 디버그: 손 지점 확인용 점
        draw_rectangle(hx - 2, hy - 2, hx + 2, hy + 2)

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
            draw_rectangle(l, b, r, t)

        if self._shield_obb:
            for i in range(4):
                x1, y1 = self._shield_obb[i]
                x2, y2 = self._shield_obb[(i + 1) % 4]
                draw_line(x1, y1, x2, y2)

    def get_obb(self):
        # 패링 중이면 방패 OBB만 충돌 대상으로 사용
        if getattr(self, 'action', None) == 'parry_hold' and self._shield_obb:
            return self._shield_obb
        # 아니면 몸통 AABB의 네 꼭짓점을 반환(기존 충돌 동작 유지)
        l, b, r, t = self.get_bb()
        return ((l, b), (r, b), (r, t), (l, t))

