from types import SimpleNamespace
import random

from pico2d import (
    SDL_KEYDOWN, SDL_KEYUP,
    SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, SDLK_KP_2,
    get_time, get_canvas_width # <--- 추가
)
from sdl2 import SDLK_KP_2

from behavior_tree import BehaviorTree, Selector, Action, Condition, Sequence
import scramble_nav

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

        self.stage = None                 # StageColliders
        self.weapon_getter = None         # 현재 "줍으러 갈" 무기를 돌려주는 함수
        self.scramble_plan = None         # scramble_nav.ScramblePlan
        self.scramble_segment_index = 0   # 현재 몇 번째 segment 수행 중인지

        # [추가] 크로스오버(구석 탈출) 전용 타이머와 방향 저장
        self.crossover_end_time = 0.0
        self.crossover_move_dir = 0

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


        # 검 모드: SwordPhaseTree (1단계 = simple 로직 래핑)


        # 공격자 행동(AttackerBehavior) – 일단은 simple 공격만
        a_sword_chase = Action('검-추격/몰기', self.act_simple_attack_mode)
        sword_attacker_behavior = Selector(
            'SwordAttackerBehavior',
            a_sword_chase,   # 나중에 TimeLowAllIn, ItemHunt, CreateAngle가 여기 추가될 예정
        )

        # 방어자 행동(DefenderBehavior) – 일단은 simple 도망만
        a_sword_flee = Action('검-도망', self.act_simple_defense_mode)
        sword_defender_behavior = Selector(
            'SwordDefenderBehavior',
            a_sword_flee,    # 나중에 EmergencyParry, RunAway, PrepareParry 붙일 자리
        )

        # 내가 들었을 때 = 공격자 트리
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
        """
        stage_colliders: StageColliders 인스턴스
        weapon_getter: 호출하면 현재 '줍으러 갈' 무기(Sword/Spear)를 돌려주는 함수
                       예) lambda: sword
        """
        self.stage = stage_colliders
        self.weapon_getter = weapon_getter

    def _reset_scramble_plan(self):
        self.scramble_plan = None
        self.scramble_segment_index = 0
        # 방향도 정리해 주는 게 깔끔함
        self._set_move_dir(0)


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
        # -------------------------------------------------------
        # 1. 기본 유효성 검사
        # -------------------------------------------------------
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
            if abs(dx) > 10.0:
                self._set_move_dir(1 if dx > 0 else -1)
            else:
                self._set_move_dir(0)  # 멈춰서 줍기 대기
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

            # 도착 확인: X좌표가 근처인가?
            if abs(target_x - self.me.x) <= 10.0:
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

            if tx1 <= self.me.x <= tx2:
                # 제자리 점프 시작
                self._set_move_dir(0)
                self._tap_jump(0.5)
            else:
                # 발사대 이동
                if self.me.x < tx1:
                    self._set_move_dir(1)
                elif self.me.x > tx2:
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