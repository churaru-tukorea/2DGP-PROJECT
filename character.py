from pico2d import load_image, get_time, SDL_KEYDOWN, SDLK_SPACE, SDLK_RIGHT, SDL_KEYUP, SDLK_LEFT
from sdl2 import SDL_KEYDOWN, SDLK_SPACE, SDLK_RIGHT, SDL_KEYUP, SDLK_LEFT, SDLK_a
# 애니 좌표/액션 인덱스:
from sprite_tuples import ACTION, sprite, sweat
from state_machine import StateMachine

class Idle:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event): pass

    def exit(self, state_event): pass

    def do(self, dt):
        self.idle_timer += dt
        if self.idle_timer >= 0.125:  # 8fps = 1/8s
            self.idle_timer -= 0.125
            self.anim_frame ^= 1  # 0 <-> 1 토글

    def draw(self):
        if not self.image:
            return
        l, b, w, h = sprite[ACTION['idle']][self.anim_frame]
        self.image.clip_draw(l, b, w, h, self.x, self.y)



class Character:
    def __init__(self, pid=1):
        self.x, self.y = 400, 90 # 이건 그냥 띄워보려는 거니까 일단 임의위치 위에 띄우려는
        self.pid = pid
        self.face_dir = +1
        self.move_dir = 0
        self.image = load_image('project_character_sheet.png')

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
        self.state_machine = StateMachine(self.IDLE,{

         }
        )

        pass

    def handle_event(self):
        self.state_machine.handle_state_event(('INPUT', event))

    def update(self):
        self.state.do(self, dt)

    def draw(self):
        self.state.draw(self)