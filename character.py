from pico2d import load_image, get_time, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_RIGHT, SDLK_LEFT, SDLK_a
# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine


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
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)

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

        STEP = 0.5
        while now >= self.boy.next_move_flip:
            self.boy.move_frame = (self.boy.move_frame + 1) % 10  # 0~9
            self.boy.next_move_flip += STEP

        l, b, w, h = sprite[ACTION['move']][self.boy.move_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y,200,200)

class Jump_Land:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_land"


    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):
        now = get_time()
        STEP = 0.1
        # one-shot: 마지막 프레임(9)에 도달하면 정지
        while now >= self.boy.next_jump_flip and self.boy.jump_frame < 9:
            self.boy.jump_frame += 1
            self.boy.next_jump_flip += STEP

        l, b, w, h = sprite[ACTION['jump_land']][self.boy.jump_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y,200,200)

class Attack_Fire:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        pass

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):

        from pico2d import get_time
        now = get_time()

        while now >= self.boy.next_idle_flip:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)

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

        from pico2d import get_time
        now = get_time()

        while now >= self.boy.next_idle_flip:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
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


        self.action = "idle"

        # 앞으로 필요할 상태용(타이머 같은것도 일단 있음)
        self.is_attack_reserved = False
        self.attack_fire_time = None
        self.signal_window_sec = 0.25
        self.parry_active_until = None
        self.parry_cooldown_until = None

        self.IDLE = Idle(self)
        self.MOVE = Move(self)
        self.JUMP = Jump_Land(self)

        self.state_machine = StateMachine(self.JUMP, {
            self.IDLE: {},
            self.MOVE: {},
            self.JUMP: {}
        })
        pass

    def handle_event(self, event):
        self.state_machine.handle_state_event(('INPUT', event))

    def update(self):
        self.state_machine.update()

    def draw(self):
        self.state_machine.draw()