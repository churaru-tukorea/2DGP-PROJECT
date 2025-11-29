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
        a_wander = Action('기본적인 배회', self.act_wander_around_enemy)
        a_fidget = Action('가끔 점프나잔동', self.act_small_fidgets)

        root = default_move = Selector('DefaultMovement', a_fidget, a_wander)

        c_anyone_has_weapon = Condition('누군가 무기 들고 있음?', self.cond_anyone_has_weapon)
        c_me_has_weapon = Condition('내가 무기 들고 있음?', self.cond_me_has_weapon)
        c_enemy_has_weapon = Condition('적이 무기 들고 있음?', self.cond_enemy_has_weapon)

        # --- 장비 상태에 따른 행동 ---
        a_attack_simple = Action('공격 모드', self.act_simple_attack_mode)
        a_defend_simple = Action('도망 모드', self.act_simple_defense_mode)

        c_scramble_target = Condition('주워야 할 무기 있음?', self.cond_scramble_target_exists)
        a_scramble_to_weapon = Action('무기 줍기 스크램블', self.act_scramble_to_weapon)

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

        scramble_phase = Sequence('둘 다 맨손이라 무기 줍기',
                                  c_scramble_target,
                                  a_scramble_to_weapon
                                  )

        root = Selector('Root',
                        weapon_equipped_phase,
                        scramble_phase,
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
        return self.me.y > getattr(self.me, 'ground_y', 90) + 10

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
        # 컨텍스트 및 무기 상태 검증
        if self.stage is None or self.weapon_getter is None:
            return BehaviorTree.FAIL
        weapon = self.weapon_getter()
        if weapon is None:
            self._reset_scramble_plan()
            return BehaviorTree.FAIL
        if self.me.weapon or self.enemy.weapon:
            self._reset_scramble_plan()
            return BehaviorTree.SUCCESS
        if getattr(weapon, 'state', None) != 'GROUND':
            self._reset_scramble_plan()
            return BehaviorTree.FAIL

        # 플랜 생성
        if self.scramble_plan is None:
            self.scramble_plan = scramble_nav.build_scramble_plan_to_point(
                self.stage, self.me.x, self.me.y, weapon.x, weapon.y
            )
            self.scramble_segment_index = 0
            if self.scramble_plan is None or not self.scramble_plan.segments:
                # Fallback: 단순 이동
                dx = weapon.x - self.me.x
                self._set_move_dir(1 if dx > 0 else -1) if abs(dx) > 3.0 else self._set_move_dir(0)
                return BehaviorTree.RUNNING

        # 경로 이탈(추락) 감지
        if self.scramble_segment_index < len(self.scramble_plan.segments):
            seg = self.scramble_plan.segments[self.scramble_segment_index]
            platforms = scramble_nav.build_platforms_from_stage(self.stage)
            target_plat_def = platforms.get(seg.platform)

            # 내 발밑이 목표보다 터무니없이 낮으면 리셋
            if target_plat_def and self.me.y < target_plat_def.T - 80:
                self._reset_scramble_plan()
                return BehaviorTree.RUNNING

        # 세그먼트 실행
        if self.scramble_segment_index >= len(self.scramble_plan.segments):
            # 도착 후 무기 줍기 미세 조정
            dx = weapon.x - self.me.x
            self._set_move_dir(1 if dx > 0 else -1) if abs(dx) > 5.0 else self._set_move_dir(0)
            return BehaviorTree.RUNNING

        seg = self.scramble_plan.segments[self.scramble_segment_index]

        # 걷기 로직
        if seg.kind == 'walk':
            target_x = seg.target_x
            if abs(target_x - self.me.x) > 10.0:
                self._set_move_dir(1 if target_x > self.me.x else -1)
            else:
                self._set_move_dir(0)
                self.scramble_segment_index += 1

        # 점프 로직
        elif seg.kind == 'jump':
            # 착지 확인: 내가 지금 목표 플랫폼 위에 있는가?
            platforms = scramble_nav.build_platforms_from_stage(self.stage)
            cur_plat = scramble_nav.find_platform_under_point(platforms, self.me.x, self.me.y)
            dest_plat_name = seg.jump_template.to_platform

            # 목표 플랫폼에 도착했으면 다음 단계로 진행
            if cur_plat and cur_plat.name == dest_plat_name:
                self.scramble_segment_index += 1
                return BehaviorTree.RUNNING

            # 점프 진행 중: 공중에 있거나, 점프 키를 누르는 중이라면?
            # -> 절대 걷기 로직으로 넘어가지 말고, '점프 방향'을 계속 유지
            # jump_end_time > 0은 현재 키를 누르고 있다는 뜻 (0.0이 될 때까지 대기)
            if self._is_in_air() or self.jump_end_time > 0:
                self._set_move_dir(seg.dir)
                return BehaviorTree.RUNNING

            # 점프 시도: 아직 출발 플랫폼에 있다면
            tx1, tx2 = seg.takeoff_range

            if tx1 <= self.me.x <= tx2:
                # 범위 안: 멈춰서 점프 실행
                self._set_move_dir(0)
                if self.jump_end_time <= 0.0:  # 쿨타임/키누름 끝났을 때만
                    self._set_move_dir(seg.dir)
                    hold_time = seg.jump_template.hold_time if seg.jump_template else 0.4
                    self._tap_jump(hold_time)
                    # 중요: 여기서 index += 1을 하지 않음! (착지할 때까지 대기)
            else:
                # 범위 밖: 도움닫기 위치로 이동
                center_x = (tx1 + tx2) / 2
                self._set_move_dir(1 if center_x > self.me.x else -1)

        return BehaviorTree.RUNNING


    # 디버그 그리기

    def draw(self):
        from pico2d import draw_rectangle, draw_line

        if not self.scramble_plan or not self.scramble_plan.segments:
            return

        # 현재 목표 세그먼트 표시
        if self.scramble_segment_index < len(self.scramble_plan.segments):
            seg = self.scramble_plan.segments[self.scramble_segment_index]

            # 1. 내가 가려는 목표 X 위치 (초록색 선)
            if seg.target_x:
                draw_line(seg.target_x, self.me.y - 50, seg.target_x, self.me.y + 50, 0, 0, 0)

            # 2. 점프 구간 표시 (붉은색 박스)
            if seg.kind == 'jump' and seg.takeoff_range:
                x1, x2 = seg.takeoff_range
                y = self.me.y
                draw_rectangle(x1, y - 10, x2, y + 10)
