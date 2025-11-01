from pico2d import load_image, get_time, SDL_KEYDOWN, SDL_KEYUP, SDLK_SPACE, SDLK_RIGHT, SDLK_LEFT, SDLK_a
# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine


class Idle:
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

        while now >= self.boy.next_idle_flip_at:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip_at += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)

class Move:
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

        while now >= self.boy.next_idle_flip_at:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip_at += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)

class Jump_Land:
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

        while now >= self.boy.next_idle_flip_at:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip_at += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)

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

        while now >= self.boy.next_idle_flip_at:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip_at += 0.125

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

        while now >= self.boy.next_idle_flip_at:
            self.boy.anim_frame ^= 1
            self.boy.next_idle_flip_at += 0.125

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y)


class Character:
    def __init__(self, pid=1):
        self.x, self.y = 400, 90 # 이건 그냥 띄워보려는 거니까 일단 임의위치 위에 띄우려는
        self.pid = pid
        self.face_dir = +1
        self.move_dir = 0
        self.image = load_image('project_character_sheet.png')

        self.next_idle_flip_at = get_time() + 0.125  # idle 8fps = 1/8초

        #애니메이션을 위한 변수들
        self.anim_frame = 0
        self.idle_timer = 0.0
        
        
        self.action = "idle"

        # 앞으로 필요할 상태용(타이머 같은것도 일단 있음)
        self.is_attack_reserved = False
        self.attack_fire_time = None
        self.signal_window_sec = 0.25
        self.parry_active_until = None
        self.parry_cooldown_until = None

        self.IDLE = Idle(self)
        self.state_machine = StateMachine(self.IDLE, {
            self.IDLE: {}
        })
        pass

    def handle_event(self, event):
        self.state_machine.handle_state_event(('INPUT', event))

    def update(self):
        self.state_machine.update()

    def draw(self):
        self.state_machine.draw()