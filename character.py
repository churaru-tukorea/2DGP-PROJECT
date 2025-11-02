from pico2d import load_image, get_time, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_RIGHT, SDLK_LEFT, SDLK_a, \
    get_canvas_height
from sdl2 import SDLK_j, SDLK_p

# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine

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
def a_down(e):
    return e[0] == 'INPUT' and e[1].type == SDL_KEYDOWN and e[1].key == SDLK_a

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
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, 200, 200)


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
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)
        elif self.boy.face_dir == -1:
            self.boy.image.clip_composite_draw(l, b, w, h, 0,'h', self.boy.x, self.boy.y, 200, 200)


class Jump_Up:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_land"
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
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, 200, 200)



class Jump_Fall:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_land"
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
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, 200, 200)
        #이것도 내려오는 이미지가 1개로 그냥 이것만 보여주는거임

class Jump_Land:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "attack_fire"
        self.boy.jump_frame = 0
        STEP = 0.05  # draw의 STEP과 동일하게
        self.boy.next_jump_flip = get_time() + STEP


    def exit(self, event):
        pass

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
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, 200, 200)

        if self.boy.jump_frame == 9:
            self.boy.state_machine.handle_state_event(('TIMEOUT', None))

class Attack_Fire:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, ev=None):
        # 애니 초기화
        self.boy.attack_frame = 0
        self._step = 1.0 / 15.0   # ~15fps
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
        while now >= self._next and self.boy.attack_frame < 6:
            self.boy.attack_frame += 1
            self._next += self._step

        # 렌더
        l, b, w, h = sprite[ACTION['attack_fire']][self.boy.attack_frame]
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y,200,200)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y,200,200)

        # 원샷 종료 시점에 복귀 이벤트 발송
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
        pass

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):
        # parry_hold는 1프레임 고정
        l, b, w, h = sprite[ACTION['parry_hold']][0]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)


class Character:
    def __init__(self, pid=1):
        self.x, self.y = 400, 90 # 이건 그냥 띄워보려는 거니까 일단 임의위치 위에 띄우려는
        self.pid = pid
        self.face_dir = +1
        self.move_dir = 0
        self.image = load_image('project_character_sheet.png')

        self.next_idle_flip = get_time() + 0.125  # idle을 넘기는 기준의 시간이 되어주는

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
        self.face_dir = +1
        self.move_dir = 0  # -1: 왼쪽, 0: 안 움직임, +1: 오른쪽

        # 물리
        self.vx = 0.0
        self.vy = 0.0
        self.move_speed = 250.0     # px/s
        self.jump_speed = 500.0     # px/s 위로
        self.gravity = -1500.0      # px/s^2
        self.max_jump_hold = 0.18   # 버튼 홀드로 더 올라갈 수 있는 시간(초)

        self.jump_pressed_time = 0.0   # 언제 점프 시작했는지
        self.last_time = get_time()    # dt 구하려고

        self.action = "idle"

        #테스트용
        self.draw_w = 200
        self.draw_h = 200
        # 캔버스 크기 받아두기
        self.canvas_h = get_canvas_height()

        # 지금은 스테이지가 없으니까, 그냥 창을 그거로 한다.
        self.ground_y = self.draw_h // 2   # 200이면 100

        # 시작 y도 이걸로 맞춰놓자
        self.x, self.y = 400, self.ground_y

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
        if event.type == SDL_KEYDOWN and event.key == SDLK_a:
            if not self.is_attack_reserved:
                self.is_attack_reserved = True
                self.attack_fire_time = get_time() + 3.0  # 3초 뒤 발동
            return  # 공격은 상태머신에 바로 전달하지 않음

        # 나머지는 상태머신에 그대로 전달
        self.state_machine.handle_state_event(('INPUT', event))
        
        
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

    def draw(self):
        self.state_machine.draw()

