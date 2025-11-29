from types import SimpleNamespace
import random

from pico2d import (
    SDL_KEYDOWN, SDL_KEYUP,
    SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, SDLK_KP_2,
    get_time, get_canvas_width # <--- 추가
)
from sdl2 import SDLK_KP_2

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

    def _tap_jump(self):
        # 이미 공중에 있거나, 점프 키를 누르는 중이면 또 누르지 않음
        if self._is_in_air() or self.jump_end_time > 0:
            return

        self._send_key(SDLK_KP_1, True)
        self.jump_end_time = get_time() + 0.2
    def _tap_attack(self):
        self._send_key(SDLK_KP_2, True)
        self._send_key(SDLK_KP_2, False)

    def _is_in_air(self):
        return self.me.y > getattr(self.me, 'ground_y', 90) + 10


    # ------------------------------------------------------------------
    #  Condition 함수들(정신없어서 나눠야겠으)
    # ------------------------------------------------------------------
    def cond_anyone_has_weapon(self): # 나 또는 적이 무기를 들고 있으면 True.
        me_has = getattr(self.me, 'weapon', None) is not None
        enemy_has = (self.enemy is not None) and (getattr(self.enemy, 'weapon', None) is not None)
        if me_has or enemy_has:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def cond_me_has_weapon(self): #내가 들고있는지
        if getattr(self.me, 'weapon', None) is not None:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def cond_enemy_has_weapon(self): #적이 들고있는지
        has_weapon = (self.enemy is not None) and (getattr(self.enemy, 'weapon', None) is not None)
        if has_weapon:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL
    # ------------------------------------------------------------------
    #  Action 함수들(정신없어서 나눠야겠으)
    # ------------------------------------------------------------------

    def act_wander_around_enemy(self):#너무 멀면 적 쪽으로 걸어가고 가까우면 멈추는 수준? 아직 지형지물 극복 방법은 안정했셔...
        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            return BehaviorTree.FAIL

        dx = enemy.x - me.x
        dist = abs(dx)

        # 떨림 방지: 접근 시작 거리와 정지 거리를 다르게 설정
        start_chase_range = 100.0  # 이보다 멀어지면 접근 시작
        stop_chase_range = 60.0  # 이보다 가까워지면 정지

        # 현재 움직이고 있는지 확인 (관성 유지용)
        is_moving = (self.me.move_dir != 0)

        should_move = False
        if is_moving:
            # 이미 움직이는 중이라면, 목표지점(60)까지 확실히 도달할 때까지 멈추지 않음
            if dist > stop_chase_range:
                should_move = True
        else:
            # 멈춰있는 상태라면, 충분히 멀어졌을 때(100) 비로소 움직임 시작
            if dist > start_chase_range:
                should_move = True

        if should_move:
            self._set_move_dir(+1 if dx > 0 else -1)
        else:
            self._set_move_dir(0)

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
        #- 내가 무기를 들고 있으면:
        #적과의 거리가 멀면 → 다가간다.
        #적과의 거리가 어느 정도면 → 가끔 공격 키를 누른다.
        #(아직 패링, 타이머, 아이템, 각 싸움 전부 무시. 정확히는 구체적으로 어떻게 할지 아직 모르겠음...)

        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            return BehaviorTree.FAIL

        dx = enemy.x - me.x
        dist = abs(dx)

        # 떨림 방지 로직 적용
        approach_start_dist = 100.0  # 접근 시작
        approach_end_dist = 70.0  # 접근 종료 (공격 사거리 안쪽)

        # 공격 쿨타임 체크 및 실행
        now = get_time()
        # 공격 범위(85) 안에 있고 쿨타임이 찼으면 공격
        if dist <= approach_end_dist + 15.0 and now >= self.next_attack_time:
            self.next_attack_time = now + random.uniform(0.6, 1.2)
            self._tap_attack()
            # 공격 중에는 잠시 멈춤
            self._set_move_dir(0)
            return BehaviorTree.SUCCESS

        # 이동 로직(적당한 거리 유지)
        is_moving = (self.me.move_dir != 0)

        should_approach = False
        if is_moving:
            if dist > approach_end_dist:  # 70까지는 계속 감
                should_approach = True
        else:
            if dist > approach_start_dist:  # 100 넘으면 출발
                should_approach = True

        if should_approach:
            self._set_move_dir(+1 if dx > 0 else -1)
        else:
            self._set_move_dir(0)

        return BehaviorTree.SUCCESS

    def act_simple_defense_mode(self): # 이것도 다순한겨 글서

        #적이 무기를 들고 있고, 나는 맨몸일 때:
        #너무 가까우면 반대 방향으로 도망
        #어느 정도 거리가 벌어지면 멈춤
        #(나중에는 여기서 패링/점프 회피 등으로 바뀔 예정. 이것도 아직 이렇게만 하는건 사실...)

        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            return BehaviorTree.FAIL

        dx = enemy.x - me.x
        dist = abs(dx)

        canvas_w = get_canvas_width()
        margin = 100.0

        escape_dir = -1 if dx > 0 else +1

        is_cornered = False
        if escape_dir == -1 and me.x < margin:
            is_cornered = True
        elif escape_dir == +1 and me.x > canvas_w - margin:
            is_cornered = True

        # 도망 떨림 방지
        flee_start_dist = 250.0  # 적이 250 안으로 들어오면 도망 시작
        flee_end_dist = 350.0  # 350만큼 벌어지면 멈춤 (충분히 도망)

        crossover_range = 250.0

        is_moving = (self.me.move_dir != 0)
        should_flee = False

        if is_cornered:
            # 구석 로직은 위급하므로 즉시 반응=
            if dist < crossover_range:
                self._set_move_dir(-escape_dir)
                if not self._is_in_air():
                    self._tap_jump()
                return BehaviorTree.SUCCESS
            else:
                self._set_move_dir(0)
                return BehaviorTree.SUCCESS

        # 일반 도망 로직 (Dead Zone)
        if is_moving:
            if dist < flee_end_dist:  # 350까지 벌어질 때까지 계속 도망
                should_flee = True
        else:
            if dist < flee_start_dist:  # 250 안으로 들어오면 도망 시작
                should_flee = True

        if should_flee:
            self._set_move_dir(escape_dir)
        else:
            self._set_move_dir(0)

        return BehaviorTree.SUCCESS
