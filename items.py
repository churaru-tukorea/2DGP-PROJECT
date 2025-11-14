from pico2d import load_image, get_time, draw_rectangle
import game_world



class SpeedClockItem:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.image = load_image('speed_clock.png')
        self.draw_w = 48
        self.draw_h = 48

    def update(self):
        pass

    def draw(self):
        self.image.clip_draw(0, 0, self.image.w, self.image.h,
                             self.x, self.y, self.draw_w, self.draw_h)
        draw_rectangle(*self.get_bb())
        pass

    def get_bb(self):
        hw = self.draw_w // 2
        hh = self.draw_h // 2
        return self.x - hw, self.y - hh, self.x + hw, self.y + hh

    def handle_collision(self, group, other):
        pass

    def apply_to(self, character):
        now = get_time()
        duration = 10.0
        end_time = now + duration

        # 남은 시간이 있으면 연장, 없으면 새로 시작
        if getattr(character, 'speed_buff_until', 0.0) > now:
            character.speed_buff_until = max(character.speed_buff_until, end_time)
        else:
            character.speed_buff_until = end_time

        # 기본값 대비 계수 
        speed_factor = 1.4  # 좌우 이동 더 빠르게
        jump_factor = 1.2  # 점프 초기속도 살짝 증가
        gravity_factor = 1.5  # 중력 더 강하게

        character.move_speed = character.base_move_speed * speed_factor
        character.jump_speed = character.base_jump_speed * jump_factor
        character.gravity = character.base_gravity * gravity_factor

        # 아이템 제거
        game_world.remove_object(self)
        pass

class AttackClockItem:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.image = load_image('attack_clock.png')
        self.draw_w = 48
        self.draw_h = 48
        pass

    def update(self):

        pass

    def draw(self):
        self.image.clip_draw(0, 0, self.image.w, self.image.h,
                             self.x, self.y, self.draw_w, self.draw_h)
        draw_rectangle(*self.get_bb())
        pass

    def get_bb(self):
        hw = self.draw_w // 2
        hh = self.draw_h // 2
        return self.x - hw, self.y - hh, self.x + hw, self.y + hh
        pass

    def handle_collision(self, group, other):
        pass

    def apply_to(self, character):
        now = get_time()
        duration = 10.0
        end_time = now + duration

        if getattr(character, 'attack_buff_until', 0.0) > now:
            character.attack_buff_until = max(character.attack_buff_until, end_time)
        else:
            character.attack_buff_until = end_time

        # 공격 차지 시간을 1.5초로 고정
        character.attack_charge_time = 1.5

        game_world.remove_object(self)
