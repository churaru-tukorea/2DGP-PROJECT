# Character의 상태 전용 모듈

from pico2d import (
    get_time,
    SDL_KEYDOWN, SDL_KEYUP,
    SDLK_LEFT, SDLK_RIGHT, SDLK_p,
)

import game_framework
import config
from sprite_tuples import ACTION, sprite

RELEASE_FRAME = 5  # ← 네가 원하는 프레임 인덱스


class Idle:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "idle"
        self.boy.move_dir = 0
        self.idle_timer = 0.0

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):

        STEP = 0.125
        self.boy.idle_timer += game_framework.frame_time

        while self.boy.idle_timer >= STEP:
            self.boy.anim_frame ^= 1
            self.boy.idle_timer -= STEP

        l, b, w, h = sprite[ACTION['idle']][self.boy.anim_frame]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)


class Move:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "move"
        self.move_timer = 0.0

    def exit(self, event):
        pass

    def do(self):
        pass

    def draw(self):

        STEP = 0.125

        self.boy.move_timer += game_framework.frame_time
        while self.boy.move_timer >= STEP:
            self.boy.move_frame = (self.boy.move_frame + 1) % 10
            self.boy.move_timer -= STEP

        l, b, w, h = sprite[ACTION['move']][self.boy.move_frame]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)


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
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)


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
        # 스테이지 충돌을 안 쓸 때만 옛 ground_y 체크
        if not getattr(self.boy, 'use_stage_collision', False):
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
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)
        # 이것도 내려오는 이미지가 1개로 그냥 이것만 보여주는거임


class Jump_Land:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, state_event):
        self.boy.action = "jump_land"
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
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)

        if self.boy.jump_frame == 9:
            self.boy.state_machine.handle_state_event(('TIMEOUT', None))


class Attack_Fire:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, ev=None):
        # 애니 초기화
        self.boy.action = "attack_fire"
        self.boy.attack_frame = 0
        self._step = 1.0 / 15.0  # ~15fps
        # self._step = 0.9  # ~15fps
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
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)

        if self.boy.attack_frame >= 6:  # 마지막 프레임
            if self._from_air:
                self.boy.state_machine.handle_state_event(('ATTACK_END_AIR', None))
            else:
                if self.boy.right_pressed or self.boy.left_pressed:
                    self.boy.state_machine.handle_state_event(('ATTACK_END_MOVE', None))
                else:
                    self.boy.state_machine.handle_state_event(('ATTACK_END_IDLE', None))


class Attack_Spear:
    def __init__(self, boy):
        self.boy = boy

    def enter(self, ev=None):
        self.boy.action = "attack_spear"
        self.boy.attack_frame = 0
        # self._step = 2.0
        self._step = 1.0 / 20.0  # 더 빠른 프레임 진행
        self._next = get_time() + self._step
        self._thrown = False
        self._anchor_y = self.boy.y

    def exit(self, ev=None):
        pass

    def do(self):
        pass

    def draw(self):

        now = get_time()
        self.boy.y = self._anchor_y

        while now >= self._next and self.boy.attack_frame < 6:
            self.boy.attack_frame += 1
            self._next += self._step

        # release frame에서 실제 투척
        if (not self._thrown) and self.boy.attack_frame == RELEASE_FRAME:
            w = getattr(self.boy, 'weapon', None)
            if w and hasattr(w, 'throw_from_owner'):
                w.throw_from_owner()
            self._thrown = True

        l, b, w, h = sprite[ACTION['attack_spear']][self.boy.attack_frame]
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)

        if self.boy.attack_frame >= 6:
            if self.boy.y > self.boy.ground_y:
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

        self.boy.move_dir = 0
        self.boy.vx = 0.0
        self.boy.right_pressed = False
        self.boy.left_pressed = False
        now = get_time()
        mode = getattr(config, 'weapon_mode', 'sword')  # 기본은 sword 가정
        if mode == 'spear':
            dur = 0.12  # 창인 경우 아주 조금
        else:
            dur = 1.0  # 검: 1초 유지

        self.boy.parry_active_until = now + dur  # 충돌 유효시간
        self.boy._parry_hold_until = now + dur  # 유지시간

    def exit(self, event):
        # 유지시간 타이머 정리
        self.boy._parry_hold_until = None

        try:
            is_p_up = (
                    isinstance(event, tuple) and event[0] == 'INPUT'
                    and getattr(event[1], 'type', None) == SDL_KEYUP
                    and getattr(event[1], 'key', None) == SDLK_p
            )
        except:
            is_p_up = False

        try:
            is_move_break = (
                    isinstance(event, tuple) and event[0] == 'INPUT'
                    and getattr(event[1], 'type', None) == SDL_KEYDOWN
                    and getattr(event[1], 'key', None) in (SDLK_LEFT, SDLK_RIGHT)
            )
        except:
            is_move_break = False

        if is_p_up or is_move_break:
            if getattr(config, 'weapon_mode', 'sword') == 'sword':
                now = get_time()
                self.boy.parry_active_until = None
                self.boy.parry_cooldown_until = now + 5.0

    def do(self):
        now = get_time()

        # 이동키로 끊기
        if self.boy.right_pressed or self.boy.left_pressed:
            if getattr(config, 'weapon_mode', 'sword') == 'sword':
                self.boy.parry_active_until = None
                self.boy.parry_cooldown_until = now + 5.0

            self.boy.state_machine.handle_state_event(('BREAK_TO_MOVE', None))
            self.boy.action = "move"
            return

        if getattr(self.boy, '_parry_hold_until', None) and now > self.boy._parry_hold_until:
            self.boy.parry_active_until = None
            self.boy.parry_cooldown_until = now + 5.0
            self.boy.state_machine.handle_state_event(('PARRY_EXPIRE', None))

    def draw(self):
        # parry_hold는 1프레임 고정
        l, b, w, h = sprite[ACTION['parry_hold']][0]
        # 방향 적용
        if self.boy.face_dir == 1:
            self.boy.image.clip_draw(l, b, w, h, self.boy.x, self.boy.y, self.boy.draw_w, self.boy.draw_h)
        else:
            self.boy.image.clip_composite_draw(l, b, w, h, 0, 'h', self.boy.x, self.boy.y, self.boy.draw_w,
                                               self.boy.draw_h)
