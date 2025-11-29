from types import SimpleNamespace
import random

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, get_time

from behavior_tree import BehaviorTree, Selector, Action, Condition, Sequence


class CharacterAI:
    def __init__(self, me, enemy):
        self.me = me          # AI가 조종할 Character (pid=2)
        self.enemy = enemy    # 상대 Character (pid=1)

        # 가상 키 입력 상태 (중복으로 주는거 방지)
        self.left_down = False
        self.right_down = False

        # 점프 쿨타임용, 디폴트일땐 적당히 이정도 기다려라...
        self.next_fidget_time = get_time() + random.uniform(1.0, 3.0)
        # 공격 쿨타임
        self.next_attack_time = get_time() + random.uniform(0.8, 1.5)

        self.jump_end_time = 0.0

        self._build_bt()

    def _build_bt(self):
        a_wander = Action('기본적인 배회', self.act_wander_around_enemy)
        a_fidget = Action('가끔 점프나잔동', self.act_small_fidgets)

        root = default_move = Selector('DefaultMovement', a_fidget, a_wander)

        c_anyone_has_weapon = Condition('누군가 무기 들고 있음?', self.cond_anyone_has_weapon)
        c_me_has_weapon = Condition('내가 무기 들고 있음?', self.cond_me_has_weapon)
        c_enemy_has_weapon = Condition('적이 무기 들고 있음?', self.cond_enemy_has_weapon)

        # --- 장비 상태에 따른 행동 ---
        a_attack_simple = Action('공격 모드', self.act_simple_attack_mode)
        a_defend_simple = Action('도망 모드', self.act_simple_defense_mode)

        attacker_branch = Sequence('Equipped-Attacker',
                                   c_me_has_weapon,
                                   a_attack_simple)

        defender_branch = Sequence('Equipped-Defender',
                                   c_enemy_has_weapon,
                                   a_defend_simple)

        equipped_role_selector = Selector('EquippedRoleSelector',
                                          attacker_branch,
                                          defender_branch)

        weapon_equipped_phase = Sequence('WeaponEquippedPhase',
                                         c_anyone_has_weapon,
                                         equipped_role_selector)

        # --- Root ---
        root = Selector('Root',
                        weapon_equipped_phase,
                        default_move)

        self.bt = BehaviorTree(root)

        self.bt = BehaviorTree(root)
    def update(self):
        self.bt.run()

        if self.jump_end_time > 0 and get_time() >= self.jump_end_time:
            self._send_key(SDLK_KP_1, False)  # 키 떼기
            self.jump_end_time = 0.0  # 리셋

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
        # 누르기만 하고, 떼는 건 나중에 함
        self._send_key(SDLK_KP_1, True)
        # 0.2초 동안 누르고 있도록 설정
        self.jump_end_time = get_time() + 0.2

    # ------------------------------------------------------------------
    #  Condition 함수들(정신없어서 나눠야겠으)
    # ------------------------------------------------------------------
    def cond_anyone_has_weapon(self): # 나 또는 적이 무기를 들고 있으면 True.
        me_has = getattr(self.me, 'weapon', None) is not None
        enemy_has = (self.enemy is not None) and (getattr(self.enemy, 'weapon', None) is not None)
        return me_has or enemy_has

    def cond_me_has_weapon(self): #내가 들고있는지
        return getattr(self.me, 'weapon', None) is not None

    def cond_enemy_has_weapon(self): #적이 들고있는지
        return (self.enemy is not None) and (getattr(self.enemy, 'weapon', None) is not None)
    # ------------------------------------------------------------------
    #  Action 함수들(정신없어서 나눠야겠으)
    # ------------------------------------------------------------------

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
        now = get_time()
        if now < self.next_fidget_time:
            # 아직 잔동 타이밍이 아니면 fail 때리고 다음 bt 차례에 wander로 가게
            return BehaviorTree.FAIL

        # 다음 잔동 시간 재설정
        self.next_fidget_time = now + random.uniform(1.0, 3.0)

        # 간단히 점프 한 번
        self._tap_jump()

        return BehaviorTree.SUCCESS

    def act_simple_attack_mode(self):#이게 단순한 공격인건 나중에 뭐가 어떻게 추가될지 몰라서...
        pass

    def act_simple_defense_mode(self): # 이것도 다순한겨 글서
        pass

