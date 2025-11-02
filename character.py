from pico2d import load_image, get_time, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_RIGHT, SDLK_LEFT, SDLK_a, \
    get_canvas_height
from sdl2 import SDLK_j, SDLK_p

# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine



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
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y,200,200)

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
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)



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
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)
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
        # 2~9까지만 돌자
        while now >= self.boy.next_jump_flip and self.boy.jump_frame < 9:
            self.boy.jump_frame += 1
            self.boy.next_jump_flip += STEP

        l, b, w, h = sprite[ACTION['jump_land']][self.boy.jump_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, 200, 200)

        if self.boy.jump_frame == 9:
            self.boy.state_machine.handle_state_event(('TIMEOUT', None))

class Attack_Fire:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "attack_fire"
        self.boy.attack_frame = 0
        STEP = 0.5  # draw의 STEP과 동일하게
        self.boy.next_attack_flip = get_time() + STEP

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):

        now = get_time()
        STEP = 0.5
        LAST = 6  # 마지막 프레임 인덱스
        while now >= self.boy.next_attack_flip and self.boy.attack_frame < LAST:
            self.boy.attack_frame += 1
            self.boy.next_attack_flip += STEP

        l, b, w, h = sprite[ACTION['attack_fire']][self.boy.attack_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y,200,200)

        # 마지막 프레임에 도달했으면 TIMEOUT 이벤트 발생시켜서 상태 전환 유도
        if self.boy.attack_frame == 6:
            self.boy.state_machine.handle_state_event(('TIMEOUT', None))

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
                a_down: self.ATTACK_FIRE,
                p_down: self.PARRY_HOLD,
            },
            self.MOVE: {
                right_down: self.MOVE,
                left_down: self.MOVE,
                right_up: self.IDLE,
                left_up: self.IDLE,
                j_down: self.JUMP_UP,
                a_down: self.ATTACK_FIRE,
                p_down: self.PARRY_HOLD,
            },
            # 위로 뜨는 중
            self.JUMP_UP: {
                # 키를 뗐거나 시간 끝나서 do()에서 'JUMP_FALL' 이벤트 던지면 여기로 감

            },
            # 떨어지는 중
            self.JUMP_FALL: {
                # 착지하면 Character.update()나 Jump_Fall.do()에서 ('LAND', None) 던짐

                lambda e: e[0] == 'LAND': self.JUMP_LAND
            },
            # 착지 애니 돌기
            self.JUMP_LAND: {
                time_out: self.IDLE
            },
            self.ATTACK_FIRE: {
                time_out: self.IDLE
            },
            self.PARRY_HOLD: {
                right_down: self.MOVE,
                left_down: self.MOVE,
                j_down: self.JUMP_UP,
            },
        })
        pass

    def handle_event(self, event):
        # 좌우 입력같은걸 다양하게 받을 것 같아서 그냥 여기에서 하는게...? 이게 최선인진 모르지만 그건 나중에.
        if event.type == SDL_KEYDOWN:
            if event.key == SDLK_RIGHT:
                self.move_dir = +1
                self.face_dir = +1
            elif event.key == SDLK_LEFT:
                self.move_dir = -1
                self.face_dir = -1
            elif event.key == SDLK_j:
                self.is_jump_key_pressed = True

        elif event.type == SDL_KEYUP:
            if event.key == SDLK_RIGHT and self.move_dir > 0:
                self.move_dir = 0
            elif event.key == SDLK_LEFT and self.move_dir < 0:
                self.move_dir = 0
            elif event.key == SDLK_j:
                self.is_jump_key_pressed = False
                # 점프 중이면 떨어지는 상태로 가라고 이벤트 던져도 됨
                self.state_machine.handle_state_event(('JUMP_FALL', None))

        self.state_machine.handle_state_event(('INPUT', event))

    def update(self):
        #생각해봤는데 상태랑 상관없이 무조건 매 프레임 돌아야 하는 애들은 그냥 한번에 여기서 계산하기로 하는게 편하지 않을까?d
        # dt 계산
        now = get_time()
        dt = now - self.last_time
        self.last_time = now

        # 가로 이동: 공중/지상 공통으로 그냥 넣자
        self.vx = self.move_speed * self.move_dir
        self.x += self.vx * dt

        # 세로 이동: 중력
        self.vy += self.gravity * dt
        self.y += self.vy * dt

        # 바닥 체크
        if self.y <= self.ground_y:
            self.y = self.ground_y
            self.vy = 0
            # 떨어지는 상태인데 바닥 닿았으면 착지로 보내기
            # (착지 상태가 아니고, 공격 중도 아닐 때만)
            self.state_machine.handle_state_event(('LAND', None))

        # 상태머신 쪽 로직도 돌리기
        self.state_machine.update()

    def draw(self):
        self.state_machine.draw()