from types import SimpleNamespace
import random

from pico2d import (
    SDL_KEYDOWN, SDL_KEYUP,
    SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, SDLK_KP_2,
    get_time, get_canvas_width # <--- 추가
)


from behavior_tree import BehaviorTree, Selector, Action, Condition, Sequence
import scramble_nav

from sword import Sword
from spear import Spear

import game_world
from items import SpeedClockItem, AttackClockItem


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

        # 라운드 타이머 – 나중에 실제 게임 타이머랑 연결할겨
        self.round_start_time = get_time()
        self.round_duration = 60.0   # 일단 60초짜리 라운드라고 가정


        self.jump_end_time = 0.0

        self.stage = None                 # StageColliders
        self.weapon_getter = None         # 현재 "줍으러 갈" 무기를 돌려주는 함수
        self.scramble_plan = None         # scramble_nav.ScramblePlan
        self.scramble_segment_index = 0   # 현재 몇 번째 segment 수행 중인지

        # [추가] 크로스오버(구석 탈출) 전용 타이머와 방향 저장
        self.crossover_end_time = 0.0
        self.crossover_move_dir = 0

        self.item_target = None
        self.item_plan = None
        self.item_segment_index = 0


        self.item_segment_start_time = 0.0

        self._build_bt()

    def _build_bt(self):
        # --- 기본 배회/잔동 ---
        a_wander = Action('기본적인 배회', self.act_wander_around_enemy)
        a_fidget = Action('가끔 점프나잔동', self.act_small_fidgets)
        default_move = Selector('DefaultMovement', a_fidget, a_wander)

        # --- 무기 소유 관련 조건 ---
        c_anyone_has_weapon = Condition('누군가 무기 들고 있음?', self.cond_anyone_has_weapon)
        c_me_has_weapon = Condition('내가 무기 들고 있음?', self.cond_me_has_weapon)
        c_enemy_has_weapon = Condition('적이 무기 들고 있음?', self.cond_enemy_has_weapon)

        # --- 무기 타입 관련 조건 (검 / 창) ---
        c_weapon_is_sword = Condition('무기 타입 == 검?', self.cond_weapon_type_sword)
        c_weapon_is_spear = Condition('무기 타입 == 창?', self.cond_weapon_type_spear)

        # --- 공용 simple 공격/도망 액션 ---
        a_attack_simple = Action('공격 모드', self.act_simple_attack_mode)
        a_defend_simple = Action('도망 모드', self.act_simple_defense_mode)

        # --- 전투 상황 관련 Condition (타이머/아이템) ---
        c_time_low = Condition('시간 임박?', self.cond_time_low)
        c_time_high = Condition('시간 여유 있음?', self.cond_time_high)
        c_item_avail = Condition('아이템 있음?', self.cond_item_available)


        # --- 검 모드: 공격자 행동(AttackerBehavior) ---

        # 기본 추격/몰기 (지금 쓰던 단순 근접전)
        a_sword_chase = Action('검-추격/몰기', self.act_simple_attack_mode)
        a_go_item = Action('아이템 먹으러 가기', self.act_go_for_item)
        a_rush = Action('RushAttack 올인 공격', self.act_rush_attack)  # 이미 짜뒀다면 그대로 사용, 없으면 나중에


        # 시간 임박 올인
        time_low_all_in = Sequence(
            'TimeLowAllIn',
            c_time_low,
            a_rush,
        )

        # 여유 있을 때 아이템 사냥
        item_hunt = Sequence(
            'ItemHunt',
            c_time_high,
            c_item_avail,
            a_go_item,
        )

        # 최종 선택자
        sword_attacker_behavior = Selector(
            'SwordAttackerBehavior',
            time_low_all_in,   # 1순위: 시간 임박하면 올인
            item_hunt,         # 2순위: 여유 있고 먹을 만한 아이템 있으면
            a_sword_chase,     # 3순위: 기본 추격/공격
        )
        # 방어자 행동(DefenderBehavior) – 일단은 simple 도망만
        a_sword_flee = Action('검-도망', self.act_simple_defense_mode)
        sword_defender_behavior = Selector(
            'SwordDefenderBehavior',
            a_sword_flee,    # 나중에 EmergencyParry, RunAway, PrepareParry 붙일 자리
        )


        sword_attacker_tree = Sequence(
            'SwordAttackerTree',
            c_me_has_weapon,
            sword_attacker_behavior,
        )

        # 적이 들었을 때 = 방어자 트리
        sword_defender_tree = Sequence(
            'SwordDefenderTree',
            c_enemy_has_weapon,
            sword_defender_behavior,
        )

        # 검 모드 공수 전환 셀렉터
        sword_role_selector = Selector(
            'SwordRoleSelector',
            sword_attacker_tree,
            sword_defender_tree,
        )

        # 무기 타입이 검일 때만 이 트리가 유효
        sword_phase_tree = Sequence(
            'SwordPhaseTree',
            c_weapon_is_sword,
            sword_role_selector,
        )


        #  모드: SpearPhaseTree (1단계 = 완전 simple 위임)


        spear_attacker_tree = Sequence(
            'SpearAttackerTree',
            c_me_has_weapon,
            a_attack_simple,
        )

        spear_defender_tree = Sequence(
            'SpearDefenderTree',
            c_enemy_has_weapon,
            a_defend_simple,
        )

        spear_role_selector = Selector(
            'SpearRoleSelector',
            spear_attacker_tree,
            spear_defender_tree,
        )

        spear_phase_tree = Sequence(
            'SpearPhaseTree',
            c_weapon_is_spear,
            spear_role_selector,
        )

        # 장비 상태 Phase 통합 (검/창 분기)


        equipped_phase_selector = Selector(
            'EquippedPhaseSelector',
            sword_phase_tree,
            spear_phase_tree,
        )

        weapon_equipped_phase = Sequence(
            'WeaponEquippedPhase',
            c_anyone_has_weapon,
            equipped_phase_selector,
        )


        # Scramble (둘 다 맨손 → 무기 줍기)


        c_scramble_target = Condition('주워야 할 무기 있음?', self.cond_scramble_target_exists)
        a_scramble_to_weapon = Action('무기 줍기 스크램블', self.act_scramble_to_weapon)

        scramble_phase = Sequence(
            '둘 다 맨손이라 무기 줍기',
            c_scramble_target,
            a_scramble_to_weapon,
        )


        # 최상위 루트

        root = Selector(
            'Root',
            weapon_equipped_phase,  # 1순위: 누군가 무기 들고 있을 때 전투
            scramble_phase,         # 2순위: 둘 다 맨손이면 무기 쟁탈전
            default_move,           # 3순위: 그냥 배회/잔동
        )

        self.bt = BehaviorTree(root)
    def update(self):

        if hasattr(self.me, 'allow_reserved_attack'):
            self.me.allow_reserved_attack = True

        self.bt.run()

        if self.jump_end_time > 0 and get_time() >= self.jump_end_time:
            self._send_key(SDLK_KP_1, False)
            self.jump_end_time = 0.0

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

    def _tap_jump(self, hold_duration=0.2):
        # 이미 공중에 있거나, 점프 키를 누르는 중이면 또 누르지 않음
        if self._is_in_air() or self.jump_end_time > 0:
            return

        self._send_key(SDLK_KP_1, True)
        # 인자로 받은 시간만큼 누르고 있게 설정 (기본값 0.2)
        self.jump_end_time = get_time() + hold_duration


    def _tap_attack(self):
        self._send_key(SDLK_KP_2, True)
        self._send_key(SDLK_KP_2, False)

    def _is_in_air(self):
        # 1. 맨바닥 체크
        if self.me.y <= getattr(self.me, 'ground_y', 90) + 10:
            return False

        # 2. 플랫폼 정밀 검사
        if self.stage:
            import scramble_nav
            platforms = scramble_nav.build_platforms_from_stage(self.stage)

            for name, p in platforms.items():
                #  X축 여유를 30 -> 60으로 대폭 증가
                # 캐릭터가 플랫폼 끝에 매달려 있어도 '땅'이라고 인정해줌
                if p.L - 60 <= self.me.x <= p.R + 60:

                    # Y축 검사 (높이 차이 60 이내)
                    diff = abs(self.me.y - p.T)

                    if diff < 60.0:
                        return False

        return True

    def set_scramble_context(self, stage_colliders, weapon_getter):
       # stage_colliders: StageColliders 인스턴스
        #weapon_getter: 호출하면 현재 '줍으러 갈' 무기(Sword/Spear)를 돌려주는 함수
        #               예) lambda: sword
        self.stage = stage_colliders
        self.weapon_getter = weapon_getter

    def _reset_scramble_plan(self):
        self.scramble_plan = None
        self.scramble_segment_index = 0
        # 방향도 정리해 주는 게 깔끔함
        self._set_move_dir(0)

    def _reset_item_plan(self):
            # 아이템 쫓아가는 플랜/인덱스 초기화
        self.item_plan = None
        self.item_segment_index = 0

         # 1) 아이템 쫓다가 눌려 있던 좌우 방향키도 정리
        self._set_move_dir(0)

        # 2) 점프 자동 홀드가 남아 있으면 여기서도 정리
        if self.jump_end_time > 0.0:
        # AI가 누른 점프 키(SDLK_KP_1) 강제로 떼기
                self._send_key(SDLK_KP_1, False)
                self.jump_end_time = 0.0

    # 공격 예약 억제 헬퍼
    def _suppress_reserved_attack_this_frame(self):
        #이 프레임 동안은 예약 공격이 발동되지 않도록 막는다.
        me = self.me
        if me is None:
            return

        #현재 프레임에는 예약 발동 금지
        if hasattr(me, 'allow_reserved_attack'):
            me.allow_reserved_attack = False

        # 이미 걸려 있던 예약도 같이 지워버린다
        if hasattr(me, 'is_attack_reserved'):
            me.is_attack_reserved = False
        if hasattr(me, 'attack_fire_time'):
            me.attack_fire_time = None

    # 속도에 따른 위치 허용 오차
    def _pos_tolerance(self, base=10.0):

        #기본 속도일 때는 base 픽셀,
        #속도가 1.4배면 그만큼 여유를 늘려서 오실레이션을 줄인다.

        me = self.me
        if me is None:
            return base

        base_speed = getattr(me, 'base_move_speed', 200.0)
        move_speed = getattr(me, 'move_speed', base_speed)

        if base_speed <= 0:
            return base

        ratio = move_speed / base_speed
        # 너무 과하게 튀지 않게 0.5~2.0 사이로 클램프
        ratio = max(0.5, min(2.0, ratio))

        return base * ratio


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

    def cond_scramble_target_exists(self):

        #둘 다 맨손이고, 스테이지 위에 'GROUND' 상태인 무기가 하나라도 있으면 True.

        # 둘 중 하나라도 무기 들고 있으면 스크램블 아님
        if self.me.weapon or self.enemy.weapon:
            self._reset_scramble_plan()
            return False

        if self.stage is None or self.weapon_getter is None:
            self._reset_scramble_plan()
            return False

        weapon = self.weapon_getter()
        if weapon is None:
            self._reset_scramble_plan()
            return False

        # Sword/Spear 둘 다 state 속성으로 상태 관리하니까 그걸 그대로 씀
        if getattr(weapon, 'state', None) != 'GROUND':
            self._reset_scramble_plan()
            return False

        return True
    def _get_current_weapon(self):
        #지금 전투에서 '주요 무기'가 무엇인지 반환.
        #- 내가 무기를 들고 있으면: 내 무기
        #- 아니면 적이 들고 있으면: 적 무기
        #- 둘 다 없으면: None

        me_weapon = getattr(self.me, 'weapon', None)
        if me_weapon is not None:
            return me_weapon

        if self.enemy is not None:
            enemy_weapon = getattr(self.enemy, 'weapon', None)
            if enemy_weapon is not None:
                return enemy_weapon

        return None

    def cond_weapon_type_sword(self):

        #현재 전투에 쓰이는 무기가 Sword 인스턴스면 SUCCESS.
        #(누가 들고 있든 상관 없음)

        w = self._get_current_weapon()
        if isinstance(w, Sword):
            return BehaviorTree.SUCCESS
        return BehaviorTree.FAIL

    def cond_weapon_type_spear(self):

        #현재 전투에 쓰이는 무기가 Spear 인스턴스면 SUCCESS.

        w = self._get_current_weapon()
        if isinstance(w, Spear):
            return BehaviorTree.SUCCESS
        return BehaviorTree.FAIL

    def _get_time_left(self):
        #라운드 남은 시간 (임시 구현)
        elapsed = get_time() - self.round_start_time
        return max(0.0, self.round_duration - elapsed)

    def cond_time_low(self):
        #남은 시간이 3초 이하인가? → 올인 모드.
        remain = self._weapon_time_left()
        if remain is None:
            return BehaviorTree.FAIL
        return BehaviorTree.SUCCESS if remain <= 3.0 else BehaviorTree.FAIL

    def cond_time_high(self):
        #남은 시간이 10초 이상인가? → 아직 여유 있음, 아이템 탐색 가능.
        remain = self._weapon_time_left()
        if remain is None:
            return BehaviorTree.FAIL
        return BehaviorTree.SUCCESS if remain >= 10.0 else BehaviorTree.FAIL


    def _weapon_time_left(self):
        #내가 들고 있는 무기의 남은 시간을 초 단위로 반환. 없으면 None.
        me = self.me
        if not getattr(me, 'weapon', None):
            return None

        pick = getattr(me, 'weapon_pick_time', 0.0)
        limit = getattr(me, 'weapon_time_limit', 0.0)
        if not pick or limit <= 0.0:
            return None

        now = get_time()
        remain = limit - (now - pick)
        return max(0.0, remain)

    def cond_item_available(self):

        #지금 나에게 '의미 있는' 아이템이 하나라도 있는가?
        #- SpeedClock: speed_buff가 꺼져 있어야 후보
        #- AttackClock: attack_buff가 꺼져 있어야 후보

        me = self.me
        if me is None:
            self._reset_item_plan()
            return BehaviorTree.FAIL

        now = get_time()
        best = None
        best_dist = None

        for layer in game_world.world:
            for obj in layer:
                # 타입 체크
                if isinstance(obj, SpeedClockItem):
                    # 이미 속도 버프 있으면 이 아이템은 건너뜀
                    if getattr(me, 'speed_buff_until', 0.0) > now:
                        continue
                elif isinstance(obj, AttackClockItem):
                    # 이미 공격 버프 있으면 건너뜀
                    if getattr(me, 'attack_buff_until', 0.0) > now:
                        continue
                else:
                    continue  # 다른 오브젝트는 무시

                # 여기까지 왔으면 "먹을 의미가 있는 아이템" 후보
                dx = obj.x - me.x
                dy = obj.y - me.y
                dist = abs(dx) + abs(dy)

                if best is None or dist < best_dist:
                    best = obj
                    best_dist = dist

        if best is None:
            # 진짜로 먹을 의미 있는 아이템이 하나도 없음
            self._reset_item_plan()  # 타겟/플랜 싹 비우기
            return BehaviorTree.FAIL

        # 먹을 만한 아이템 하나 발견
        self.item_target = best
        return BehaviorTree.SUCCESS

    # ------------------------------------------------------------------
    #  Action 함수들(정신없어서 나눠야겠으)
    # ------------------------------------------------------------------

    def act_wander_around_enemy(self):#너무 멀면 적 쪽으로 걸어가고 가까우면 멈추는 수준? 아직 지형지물 극복 방법은 안정했셔...
        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            return BehaviorTree.FAIL

        if self._is_in_air():
            return BehaviorTree.SUCCESS

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

    def act_simple_attack_mode(self):
        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            return BehaviorTree.FAIL

        dx = enemy.x - me.x
        dist = abs(dx)

        now = get_time()

        # -----------------------------
        # 거리 기준 (필요하면 숫자는 나중에 조정)
        # -----------------------------
        attack_dist = 60.0  # 이 안까지 들어오면 공격 시도
        start_move_dist = 120.0  # 이 이상 떨어져 있으면 무조건 쫓아가기

        # 1) 공격 시도: 충분히 붙었고, 쿨타임도 끝났으면
        if dist <= attack_dist and now >= self.next_attack_time:
            # 공중에서 이상하게 칼 휘두르는 거 방지
            if not self._is_in_air():
                # 멈추고 한 번 공격
                self._set_move_dir(0)
                self._tap_attack()
                # 다음 공격까지 대기 시간 (너무 자주 휘두르지 않게)
                self.next_attack_time = now + random.uniform(0.7, 1.2)
                return BehaviorTree.SUCCESS

        # 2) 아직 사거리 밖이면 → 무조건 적 쪽으로 이동
        if dist > attack_dist:
            move_dir = 1 if dx > 0 else -1
            self._set_move_dir(move_dir)
        else:
            # 사거리 안인데 쿨만 기다리는 중이면 제자리에서 버티기
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

        now = get_time()

        # 크로스오버(구석 탈출) 실행 중인지 확인 (Commitment)
        if now < self.crossover_end_time:
            # 설정된 시간 동안은 무조건 저장된 방향으로 밀고 나간다. (판단 금지)
            self._set_move_dir(self.crossover_move_dir)

            # 만약 도중에 바닥에 닿았는데 아직도 적과 겹쳐 있다면 점프 한번 더 시도
            if not self._is_in_air() and abs(enemy.x - me.x) < 30.0:
                self._tap_jump()

            return BehaviorTree.SUCCESS

        # [2] 상황 판단 로직 시작
        dx = enemy.x - me.x
        dist = abs(dx)

        canvas_w = get_canvas_width()
        margin = 100.0

        # 도망 방향 (적 반대)
        escape_dir = -1 if dx > 0 else +1

        # 구석 체크
        is_cornered = False
        if escape_dir == -1 and me.x < margin:
            is_cornered = True
        elif escape_dir == +1 and me.x > canvas_w - margin:
            is_cornered = True

        crossover_range = 250.0

        # [3] 구석 탈출 결심 (Trigger)
        if is_cornered and dist < crossover_range:
            # "지금부터 1.0초 동안은 무조건 적 방향으로 뚫고 나간다"고 서약
            self.crossover_end_time = now + 1.0
            self.crossover_move_dir = -escape_dir  # 적 방향(뚫고 나갈 방향) 저장

            # 초기 동작 실행
            self._tap_jump()
            self._set_move_dir(self.crossover_move_dir)

            return BehaviorTree.SUCCESS

        # [4] 일반 도망 (Air Lock 포함)
        if self._is_in_air():
            return BehaviorTree.SUCCESS

        flee_start_dist = 250.0
        flee_end_dist = 350.0

        is_moving = (self.me.move_dir != 0)
        should_flee = False

        if is_moving:
            if dist < flee_end_dist: should_flee = True
        else:
            if dist < flee_start_dist: should_flee = True

        if should_flee:
            self._set_move_dir(escape_dir)
        else:
            self._set_move_dir(0)

        return BehaviorTree.SUCCESS

    def act_scramble_to_weapon(self):

        # 스크램블 중에는 공격 예약이 끼어들면 경로가 꼬이니까, 이 프레임엔 무조건 막아버림
        self._suppress_reserved_attack_this_frame()

        # 기본 유효성 검사

        if self.stage is None or self.weapon_getter is None: return BehaviorTree.FAIL

        weapon = self.weapon_getter()
        # 무기가 없거나, 누가 이미 들었으면 중단
        if weapon is None or self.me.weapon or self.enemy.weapon:
            self._reset_scramble_plan()
            return BehaviorTree.SUCCESS  # 상황 종료

        # 무기가 땅에 없으면(누가 잡았거나 날아다니면) 실패 처리
        if getattr(weapon, 'state', None) != 'GROUND':
            self._reset_scramble_plan()
            return BehaviorTree.FAIL

        # -------------------------------------------------------
        # 2. 플랜 생성 (경로가 없으면 만듦)
        # -------------------------------------------------------
        if self.scramble_plan is None:
            self.scramble_plan = scramble_nav.build_scramble_plan_to_point(
                self.stage, self.me.x, self.me.y, weapon.x, weapon.y
            )
            self.scramble_segment_index = 0

            # 경로 생성 실패 시 -> 단순 무식하게 무기 쪽으로 이동 (Fallback)
            if self.scramble_plan is None or not self.scramble_plan.segments:
                dx = weapon.x - self.me.x
                if abs(dx) > 5.0:
                    self._set_move_dir(1 if dx > 0 else -1)
                else:
                    self._set_move_dir(0)
                return BehaviorTree.RUNNING

        # -------------------------------------------------------
        # 3. 계획 완료(도착) 처리
        # -------------------------------------------------------
        if self.scramble_segment_index >= len(self.scramble_plan.segments):
            # 경로 끝났는데 무기랑 높이 차이가 크다? -> 잘못 온 거임. 리셋.
            if abs(self.me.y - weapon.y) > 80.0:
                self._reset_scramble_plan()
                return BehaviorTree.RUNNING

            # 높이 맞으면 가서 줍기 (미세 조정)
            dx = weapon.x - self.me.x
            tol = self._pos_tolerance(base=10.0)

            if abs(dx) > tol:
                self._set_move_dir(1 if dx > 0 else -1)
            else:
                self._set_move_dir(0)
            return BehaviorTree.RUNNING

        # -------------------------------------------------------
        # 4. 세그먼트 실행 (여기가 핵심 수정됨)
        # -------------------------------------------------------
        seg = self.scramble_plan.segments[self.scramble_segment_index]

        # 디버그 출력
        print(f"[AI-RUN] Seg[{self.scramble_segment_index}] {seg.kind.upper()} | "
              f"Me:({self.me.x:.1f}, {self.me.y:.1f}) | Dir:{self.me.move_dir}")

        if seg.kind == 'walk':
            dist = seg.target_x - self.me.x
            print(f"       Target X: {seg.target_x:.1f} | Dist: {dist:.1f} | Blocked? {dist * self.me.move_dir < 0}")
            # Blocked? 가 True면 벽에 막혀서 못 가는데 걷고 있다는 뜻

        elif seg.kind == 'jump':
            tx1, tx2 = seg.takeoff_range
            in_range = (tx1 <= self.me.x <= tx2)
            print(f"       Jump Range: {tx1:.1f}~{tx2:.1f} | InRange: {in_range} | Air: {self._is_in_air()}")
        # ---------------------------------------------------
        # [A] 걷기 (Walk)
        if seg.kind == 'walk':
            target_x = seg.target_x
            tol = self._pos_tolerance(base=10.0)

            # 도착 확인: X좌표가 근처인가?
            if abs(target_x - self.me.x) <= tol:
                self._set_move_dir(0)
                self.scramble_segment_index += 1  # 다음 단계로!
            else:
                self._set_move_dir(1 if target_x > self.me.x else -1)

            return BehaviorTree.RUNNING

            # [B] 점프 (Jump)
        elif seg.kind == 'jump':


            # 목표 플랫폼 정보
            #seg = self.scramble_plan[self.scramble_segment_index]
            dest_plat_name = seg.jump_template.to_platform

            is_hard_diagonal = False
            if seg.kind == 'jump' and seg.jump_template:
                fp = seg.jump_template.from_platform
                tp = seg.jump_template.to_platform
                if (fp, tp) in (('r3_L2', 'r2_L'), ('r3_R1', 'r2_R')):
                    is_hard_diagonal = True

            platforms = scramble_nav.build_platforms_from_stage(self.stage)
            dest_plat = platforms.get(dest_plat_name)



            # 목표 높이 (없으면 내 머리 위 100)
            target_height = dest_plat.T if dest_plat else (self.me.y + 100.0)



            # ---------------------------------------------------
            # 1. 착지 성공 확인 (Landing Check) - [대폭 수정]
            # ---------------------------------------------------
            # [중요] 올라가는 중(vy > 0)에는 절대 착지 판정을 하지 않는다!
            # 떨어지는 중(vy <= 0)이거나, 이미 땅에 붙었을 때만 체크한다.
            # self.me.vy가 없다면 velocity_y 등으로 변수명 확인 필요 (보통 vy 사용)
            is_falling = getattr(self.me, 'vy', 0) <= 0

            if not self._is_in_air() and dest_plat and is_falling:
                if abs(self.me.y - dest_plat.T) < 60.0:
                    self.jump_end_time = 0.0
                    self._send_key(SDLK_KP_1, False)
                    self._set_move_dir(0)
                    self.scramble_segment_index += 1
                    return BehaviorTree.RUNNING

            # ---------------------------------------------------
            # 2. 공중 제어 (Air Control) - [안전 높이 수정]
            # ---------------------------------------------------
            if self._is_in_air() or (self.jump_end_time > 0 and get_time() < self.jump_end_time):

                # [Case A] 특수 대각선 점프 (1층 -> 2층)
                # : 높이를 기다리지 않고, 점프 시작하자마자 바로 옆으로 민다.
                if is_hard_diagonal:
                    self._set_move_dir(seg.dir)      # 즉시 가로 이동 (방향키 누름)
                    self._send_key(SDLK_KP_1, True)  # 점프키 꾹 유지 (최대 높이)
                    self.jump_end_time = get_time() + 0.1 # 홀드 시간 갱신

                # [Case B] 일반 점프 (그 외 모든 상황: 2층->3층 등)
                # : "ㄱ"자 이동 (머리 박지 않게 충분히 뜰 때까지 X축 이동 제한)
                else:
                    # 목표 높이보다 최소 50px은 더 높아야 안전하다고 판단
                    safe_threshold = target_height + 80.0

                    if self.me.y < safe_threshold:
                        # 높이가 부족하다 -> 무조건 수직 상승 (X축 입력 0)
                        self._set_move_dir(0)
                        # 중력을 이기기 위해 점프 키 강제 유지
                        self._send_key(SDLK_KP_1, True)
                        self.jump_end_time = get_time() + 0.1
                    else:
                        # 높이 확보됨 -> 이제 옆으로 진입
                        self._set_move_dir(seg.dir)

                return BehaviorTree.RUNNING

            # ---------------------------------------------------
            # 3. 점프 시도 (Takeoff)
            # ---------------------------------------------------
            tx1, tx2 = seg.takeoff_range

            # 속도가 빨라질수록 '발사대에 올랐다'고 인정하는 범위를 넓게 잡는다
            margin = self._pos_tolerance(base=5.0)
            ex1 = tx1 - margin
            ex2 = tx2 + margin

            # 발사대 근처(ex1~ex2)에 들어왔으면 여기서 점프해도 된다고 본다
            if ex1 <= self.me.x <= ex2:
                self._set_move_dir(0)
                hold_time = seg.jump_template.hold_time if seg.jump_template else 0.5
                self._tap_jump(hold_time)

            # 아직 너무 왼쪽/오른쪽이면 중심 쪽으로 이동
            else:
                center = (tx1 + tx2) * 0.5
                if self.me.x < center:
                    self._set_move_dir(1)
                else:
                    self._set_move_dir(-1)

            return BehaviorTree.RUNNING


    # 디버그 그리기

    def draw(self):
        from pico2d import draw_rectangle, draw_line
        import scramble_nav

        if not self.scramble_plan or not self.scramble_plan.segments:
            return

        platforms = scramble_nav.build_platforms_from_stage(self.stage)
        idx = self.scramble_segment_index

        if idx < len(self.scramble_plan.segments):
            seg = self.scramble_plan.segments[idx]

            # --- 타겟 라인 그리기 로직 개선 ---
            draw_target_x = None

            if seg.kind == 'walk':
                draw_target_x = seg.target_x
            elif seg.kind == 'jump':
                # 점프 중일 때는 '다음 세그먼트(착지할 곳)'의 타겟을 미리 보여줌!
                if idx + 1 < len(self.scramble_plan.segments):
                    next_seg = self.scramble_plan.segments[idx + 1]
                    if next_seg.kind == 'walk':
                        draw_target_x = next_seg.target_x

                # 다음 타겟이 없으면(마지막 점프), 발사대 중앙이라도 보여줌
                if draw_target_x is None and seg.takeoff_range:
                    draw_target_x = (seg.takeoff_range[0] + seg.takeoff_range[1]) * 0.5

            if draw_target_x is not None:
                draw_line(draw_target_x, 0, draw_target_x, 1000, 0, 255, 0)
            # -------------------------------

            # 점프 발사대 박스 (기존 유지)
            if seg.kind == 'jump' and seg.takeoff_range:
                x1, x2 = seg.takeoff_range
                current_plat = platforms.get(seg.platform)
                y = current_plat.T if current_plat else self.me.y
                draw_rectangle(x1, y - 5, x2, y + 5)

    def act_rush_attack(self):

        #시간 임박 시 사용하는 올인 공격 모드.
        #항상 적 방향으로 전진
        #일정 거리 안에서는 쿨을 짧게 잡고 공격 난사
        enemy = self.enemy
        me = self.me

        if enemy is None or me is None:
            return BehaviorTree.FAIL

        dx = enemy.x - me.x
        dist = abs(dx)
        now = get_time()

        # 항상 적 방향으로 밀어붙이기
        move_dir = 1 if dx > 0 else -1
        self._set_move_dir(move_dir)

        # 너무 멀면 그냥 쫓기만 한다
        if dist > 180.0:
            return BehaviorTree.SUCCESS

        # 충분히 붙었으면 공격 난사 (쿨을 짧게)
        if not self._is_in_air() and now >= self.next_attack_time:
            self._tap_attack()
            self.next_attack_time = now + random.uniform(0.3, 0.6)  # 평소보다 훨씬 공격적
        return BehaviorTree.SUCCESS

    def act_go_for_item(self):
        # -------------------------------------------------------
        # 1. 기본 유효성 검사
        # -------------------------------------------------------
        self._suppress_reserved_attack_this_frame()
        me = self.me
        if me is None or self.stage is None:
            self._reset_item_plan()
            return BehaviorTree.FAIL

        target = self.item_target
        if target is None:
            self._reset_item_plan()
            return BehaviorTree.FAIL

        # [버프 체크] 이미 버프가 있으면 포기
        now = get_time()
        if isinstance(target, SpeedClockItem) and getattr(me, 'speed_buff_until', 0.0) > now:
            self._reset_item_plan()
            return BehaviorTree.FAIL
        if isinstance(target, AttackClockItem) and getattr(me, 'attack_buff_until', 0.0) > now:
            self._reset_item_plan()
            return BehaviorTree.FAIL

        # -------------------------------------------------------
        # 2. 플랜 생성
        # -------------------------------------------------------
        if self.item_plan is None:
            self.item_plan = scramble_nav.build_scramble_plan_to_point(
                self.stage, me.x, me.y, target.x, target.y
            )
            self.item_segment_index = 0

            if self.item_plan is None or not self.item_plan.segments:
                dx = target.x - me.x
                if abs(dx) > 5.0:
                    self._set_move_dir(1 if dx > 0 else -1)
                else:
                    self._set_move_dir(0)
                return BehaviorTree.RUNNING

        # -------------------------------------------------------
        # 3. 계획 완료(도착) 처리
        # -------------------------------------------------------
        if self.item_segment_index >= len(self.item_plan.segments):
            # [수정] 무기 로직처럼 80.0으로 넉넉하게
            if abs(me.y - target.y) > 80.0:
                self._reset_item_plan()
                return BehaviorTree.RUNNING

            dx = target.x - me.x
            # [수정] 무기 로직처럼 _pos_tolerance 사용
            tol = self._pos_tolerance(base=10.0)

            if abs(dx) > tol:
                self._set_move_dir(1 if dx > 0 else -1)
            else:
                self._set_move_dir(0)
                # 아이템 먹기는 성공 처리 (다음 틱에 사라지면 FAIL 되어 자연스럽게 종료)
                return BehaviorTree.SUCCESS
            return BehaviorTree.RUNNING

        # -------------------------------------------------------
        # 4. 세그먼트 실행
        # -------------------------------------------------------
        seg = self.item_plan.segments[self.item_segment_index]

        # [A] 걷기 (Walk)
        if seg.kind == 'walk':
            dist = seg.target_x - me.x
            # [수정] 무기 로직과 동일하게 _pos_tolerance 사용 (유연한 도착 판정)
            tol = self._pos_tolerance(base=10.0)

            if abs(dist) <= tol:
                self._set_move_dir(0)
                self.item_segment_index += 1
            else:
                self._set_move_dir(1 if dist > 0 else -1)
            return BehaviorTree.RUNNING

        # [B] 점프 (Jump)
        elif seg.kind == 'jump':
            tx1, tx2 = seg.takeoff_range

            # [수정] 무기 로직처럼 마진을 줘서 발사대 인식을 넉넉하게
            margin = self._pos_tolerance(base=5.0)
            ex1 = tx1 - margin
            ex2 = tx2 + margin

            # [Step 1] 발사대까지 걷기 (범위 밖이면 무조건 걷기)
            if not (ex1 <= me.x <= ex2):
                center = (tx1 + tx2) * 0.5  # 중심을 향해 걷는다
                if me.x < center:
                    self._set_move_dir(1)
                else:
                    self._set_move_dir(-1)
                return BehaviorTree.RUNNING

            # [Step 2] 발사대 도착 & 점프 로직
            dest_plat_name = seg.jump_template.to_platform
            platforms = scramble_nav.build_platforms_from_stage(self.stage)
            dest_plat = platforms.get(dest_plat_name)

            target_height = dest_plat.T if dest_plat else (me.y + 100.0)

            # [대각선 판별] mid_top, 2층 갈 때는 대각선 점프
            is_hard_diagonal = False
            is_from_center_1f = seg.platform in ['r3_L2', 'r3_R1']
            is_to_high_ground = dest_plat_name in ['r2_L', 'r2_R', 'mid_top']

            if is_from_center_1f and is_to_high_ground:
                is_hard_diagonal = True

            # (1) 착지 성공 확인
            is_falling = getattr(me, 'vy', 0) <= 0
            if not self._is_in_air() and dest_plat and is_falling:
                # [수정] 60.0으로 넉넉하게
                if abs(me.y - dest_plat.T) < 60.0:
                    self.jump_end_time = 0.0
                    self._send_key(SDLK_KP_1, False)
                    self._set_move_dir(0)
                    self.item_segment_index += 1
                    return BehaviorTree.RUNNING

            # (2) 공중 제어 (Air Control)
            if self._is_in_air() or (self.jump_end_time > 0 and get_time() < self.jump_end_time):

                if is_hard_diagonal:
                    self._set_move_dir(seg.dir)
                    # [수정] 대각선 점프는 공중에서도 점프 키 유지 (높이 확보)
                    self._send_key(SDLK_KP_1, True)
                    self.jump_end_time = get_time() + 0.1
                else:
                    # 일반 점프 (엘리베이터)
                    safe_height = target_height + 50.0  # 50.0 (무기 로직 동일)
                    if me.y < safe_height:
                        self._set_move_dir(0)
                        self._send_key(SDLK_KP_1, True)
                        self.jump_end_time = get_time() + 0.1
                    else:
                        self._set_move_dir(seg.dir)
                return BehaviorTree.RUNNING

            # (3) 점프 시도 (Takeoff)
            self._set_move_dir(0)
            hold_time = seg.jump_template.hold_time if seg.jump_template else 0.6
            self._tap_jump(hold_time)

            if is_hard_diagonal:
                self._set_move_dir(seg.dir)

            return BehaviorTree.RUNNING

        return BehaviorTree.RUNNING