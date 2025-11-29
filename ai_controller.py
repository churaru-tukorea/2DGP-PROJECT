from types import SimpleNamespace
import random

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, get_time

from behavior_tree import BehaviorTree, Selector, Action


class CharacterAI:
    def __init__(self, me, enemy):
        pass
    def _build_bt(self):
        pass

    def update(self):
        pass

    def _send_key(self, sdl_key, is_down: bool): # 특정 키를 입력한다는 헬퍼를 보내버리는
        pass
    def _set_move_dir(self, dir_x: int):    #현재 이동방향이 어딘지 계속 세팅하는.
        pass
    def _tap_jump(self): # 짧게 점프 누르고 때는. 점프하는 키 눌렀다가 때는 정도면 될듯?
        pass
    def act_wander_around_enemy(self):#너무 멀면 적 쪽으로 걸어가고 가까우면 멈추는 수준? 아직 지형지물 극복 방법은 안정했셔...
        pass
    def act_small_fidgets(self):#습관성 점프. ai가 디폴트라고 멀뚱멀뚱 왔다갔다만 하면 짜침;;
        pass
