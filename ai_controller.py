from types import SimpleNamespace
import random

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, get_time

from behavior_tree import BehaviorTree, Selector, Action


class CharacterAI:
    def __init__(self, me, enemy):
        self.me = me          # AI가 조종할 Character (pid=2)
        self.enemy = enemy    # 상대 Character (pid=1)

        # 가상 키 입력 상태 (중복으로 주는거 방지)
        self.left_down = False
        self.right_down = False

        # 점프 쿨타임용, 디폴트일땐 적당히 이정도 기다려라...
        self.next_fidget_time = get_time() + random.uniform(1.0, 3.0)

        self._build_bt()

    def _build_bt(self):
        a_wander = Action('기본적인 배회', self.act_wander_around_enemy)
        a_fidget = Action('가끔 점프나잔동', self.act_small_fidgets)

        root = default_move = Selector('DefaultMovement', a_wander, a_fidget)


        self.bt = BehaviorTree(root)
    def update(self):
        self.bt.run()

    def _send_key(self, sdl_key, is_down: bool): # 특정 키를 입력한다는 헬퍼를 보내버리는
        event_type = SDL_KEYDOWN if is_down else SDL_KEYUP
        event = SimpleNamespace(type=event_type, key=sdl_key)
        # Character.handle_event()를 그대로 재사용
        self.me.handle_event(event)

    def _set_move_dir(self, dir_x: int):    #현재 이동방향이 어딘지 계속 세팅하는.
        if dir_x < 0:
            # 왼쪽 누르고, 오른쪽은 떼기
            if not self.left_down:
                self._send_key(SDLK_LEFT, True)
                self.left_down = True
            if self.right_down:
                self._send_key(SDLK_RIGHT, False)
                self.right_down = False
        elif dir_x > 0:
            # 오른쪽 누르고, 왼쪽은 떼기
            if not self.right_down:
                self._send_key(SDLK_RIGHT, True)
                self.right_down = True
            if self.left_down:
                self._send_key(SDLK_LEFT, False)
                self.left_down = False
        else:
            # 둘 다 떼기
            if self.left_down:
                self._send_key(SDLK_LEFT, False)
                self.left_down = False
            if self.right_down:
                self._send_key(SDLK_RIGHT, False)
                self.right_down = False


    def _tap_jump(self): # 짧게 점프 누르고 때는. 점프하는 키 눌렀다가 때는 정도면 될듯?
        self._send_key(SDLK_KP_1, True)
        self._send_key(SDLK_KP_1, False)

    def act_wander_around_enemy(self):#너무 멀면 적 쪽으로 걸어가고 가까우면 멈추는 수준? 아직 지형지물 극복 방법은 안정했셔...
        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            # 적 정보가 없으면 그냥 FAIL 하자. 이게 한명이 죽었는데도 방방 뛰면 뭔가 통제안되는 느낌.
            return BehaviorTree.FAIL

        dx = enemy.x - me.x

        stop_range = 60.0
        if abs(dx) < stop_range:
            # 적과 너무 붙었으면 멈추기
            self._set_move_dir(0)
            return BehaviorTree.SUCCESS

        # 적이 오른쪽에 있으면 오른쪽, 왼쪽에 있으면 왼쪽으로 이동
        if dx > 0:
            self._set_move_dir(+1)
        else:
            self._set_move_dir(-1)

        return BehaviorTree.SUCCESS
    def act_small_fidgets(self):#습관성 점프. ai가 디폴트라고 멀뚱멀뚱 왔다갔다만 하면 짜침;;
        pass
