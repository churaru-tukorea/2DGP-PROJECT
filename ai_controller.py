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

        self.item_plan_fail_count = 0

        self.nav_mode = 'NONE'

        # CHASE 전용 경로/세그먼트 상태
        self.chase_plan = None
        self.chase_segment_index = 0
        self.chase_target_snapshot = None  # SimpleNamespace(x, y, platform_name, time)
        self.chase_segment_start_time = 0.0
        self.chase_stuck_timeout = 2.0     # 한 세그먼트에서 최대 허용 시간(초)

        # 적 점프 감지용 상태 (공격 모드에서 점프 따라하기용)
        self.enemy_prev_in_air = False
        self.enemy_last_jump_detect_time = 0.0


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

        c_enemy_on_diff_platform = Condition('적이 다른 플랫폼에 있음?', self.cond_enemy_on_different_platform)
        a_chase_enemy_nav = Action('플랫폼 네비로 적 추격', self.act_chase_enemy_nav)

        cross_platform_chase = Sequence(
            'CrossPlatformChase',
            c_enemy_on_diff_platform,
            a_chase_enemy_nav,
        )


        # 최종 선택자
        sword_attacker_behavior = Selector(
            'SwordAttackerBehavior',
            time_low_all_in,
            item_hunt,
            cross_platform_chase,
            a_sword_chase,
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
        # 매 프레임 공격 예약 허용 플래그 초기화
        if hasattr(self.me, 'allow_reserved_attack'):
            self.me.allow_reserved_attack = True

        now = get_time()

        # 적 점프 감지 (지상 -> 공중 전환 순간 기록)
        if self.enemy is not None and self.stage is not None:
            enemy_in_air = self._is_actor_in_air(self.enemy)
        else:
            enemy_in_air = False

        if enemy_in_air and not self.enemy_prev_in_air:
            # 방금 지상에서 점프한 순간
            self.enemy_last_jump_detect_time = now
        self.enemy_prev_in_air = enemy_in_air

        # BT 실행
        self.bt.run()

        # 점프 키 홀드 해제
        if self.jump_end_time > 0 and now >= self.jump_end_time:
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

    def _compute_drop_dir(self, seg, platforms):

        #drop 세그먼트에서 쓸 가로 방향을 결정한다.
        #- 1순위: jump_template.dir 이 -1 또는 +1 이면 그걸 신뢰
        #- 2순위: landing_range 중앙을 기준으로 현재 위치와 비교
        #- 3순위: 화면 중앙을 기준으로 안쪽(센터) 방향으로 이동

        # 템플릿에 명시된 dir이 -1/1이면 그대로 사용
        if seg.jump_template and seg.jump_template.dir in (-1, 1):
            return seg.jump_template.dir

        # landing_range가 있다면 그 중앙으로 향하게
        if seg.landing_range:
            lnd_x1, lnd_x2 = seg.landing_range
            lnd_cx = 0.5 * (lnd_x1 + lnd_x2)

            if self.me.x < lnd_cx - 1.0:
                return +1
            elif self.me.x > lnd_cx + 1.0:
                return -1
            # 거의 중앙이면 굳이 안 움직여도 되지만,
            # 그래도 떨어지려면 어느 쪽이든 하나 방향을 정해줘야 하니까,
            # 아래 fallback으로 넘긴다.

        # fallback: 화면 중앙 쪽으로 이동 (벽 쪽에 붙어 죽는 상황 방지)
        from pico2d import get_canvas_width
        mid = get_canvas_width() * 0.5
        return +1 if self.me.x < mid else -1

    def _reset_chase_plan(self):   #플랫폼 추격용 경로/세그먼트 상태만 정리

        self.chase_plan = None
        self.chase_segment_index = 0
        self.chase_target_snapshot = None
        self.chase_segment_start_time = 0.0
        # 이동 멈춤
        self._set_move_dir(0)

    def _switch_nav_mode(self, new_mode: str):

        #네비게이션 모드 전환.
        #- 공중에서는 SCRAMBLE/ITEM/CHASE 같은 '새 네비'로 진입하지 않는다.
        #- NONE 으로 내려가는 건 언제든 허용.

        if new_mode == self.nav_mode:
            return BehaviorTree.SUCCESS

        # 공중에서는 새로운 네비 모드로 진입 금지 (버그 예방)
        if self._is_in_air() and new_mode != 'NONE':
            return BehaviorTree.FAIL

        # 이전 모드 정리
        if self.nav_mode == 'SCRAMBLE':
            self._reset_scramble_plan()
        elif self.nav_mode == 'ITEM':
            self._reset_item_plan()
        elif self.nav_mode == 'CHASE':
            self._reset_chase_plan()

        self.nav_mode = new_mode
        return BehaviorTree.SUCCESS

    def _build_platforms(self):
        #현재 stage_colliders 기준 플랫폼 딕셔너리 생성.
        if not self.stage:
            return {}
        return scramble_nav.build_platforms_from_stage(self.stage)

    def _get_platform_for(self, actor):
        #상대가 서 있는 플랫폼 반환.
        if not self.stage or actor is None:
            return None
        platforms = self._build_platforms()
        return scramble_nav.find_platform_under_point(platforms, actor.x, actor.y)

    def _is_actor_in_air(self, actor):   #self._is_in_air 와 같은 로직을, 임의 플레이어에 대해 사용.
        if actor is None:
            return False

        if actor.y <= getattr(actor, 'ground_y', 90) + 10:
            return False

        if self.stage:
            platforms = self._build_platforms()
            for name, p in platforms.items():
                if p.L - 60 <= actor.x <= p.R + 60:
                    diff = abs(actor.y - p.T)
                    if diff < 60.0:
                        return False

        return True

    def _dbg(self, msg: str): #아오 디버그시치
        print(f"[AI-DBG] {msg}")



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
        me = self.me
        if me is None:
            return BehaviorTree.FAIL

        now = get_time()
        best = None
        best_dist = None

        # 디버그: 아이템 검색 시작
        # print("[Cond-Item] Scanning for items...")

        for layer in game_world.world:
            for obj in layer:
                if isinstance(obj, SpeedClockItem):
                    if getattr(me, 'speed_buff_until', 0.0) > now:
                        # print("  -> SpeedBuff Active. Skip.")
                        continue
                elif isinstance(obj, AttackClockItem):
                    if getattr(me, 'attack_buff_until', 0.0) > now:
                        # print("  -> AttackBuff Active. Skip.")
                        continue
                else:
                    continue

                dx = obj.x - me.x
                dy = obj.y - me.y
                dist = abs(dx) + abs(dy)

                if best is None or dist < best_dist:
                    best = obj
                    best_dist = dist


        if best is None:
            # print("[Cond-Item] No valid item found.")
            self._reset_item_plan()
            return BehaviorTree.FAIL

        # print(f"[Cond-Item] Target Found: {best} at ({best.x:.0f}, {best.y:.0f})")
        self.item_target = best
        return BehaviorTree.SUCCESS

    # Condition: 적이 다른 플랫폼에 있는가?
    def cond_enemy_on_different_platform(self):
        if self.stage is None or self.me is None or self.enemy is None:
            return BehaviorTree.FAIL

        me_plat = self._get_platform_for(self.me)
        enemy_plat = self._get_platform_for(self.enemy)

        # 플랫폼 정보를 못 찾으면 플랫폼 네비를 쓰지 않는다.
        if me_plat is None or enemy_plat is None:
            return BehaviorTree.FAIL

        # 다른 플랫폼일 때만 CHASE 시도
        if me_plat.name != enemy_plat.name:
            return BehaviorTree.SUCCESS

        # 같은 플랫폼이면, 혹시 남아 있던 CHASE 상태 정리
        if self.nav_mode == 'CHASE':
            self._switch_nav_mode('NONE')
        return BehaviorTree.FAIL

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


        attack_dist = 60.0  # 공격 사거리

        # [수정 핵심] 속도에 따른 오차 범위(Tolerance) 적용!
        # 속도가 빠르면 멈추는 거리를 좀 더 넉넉하게 잡아준다.
        tol = self._pos_tolerance(base=10.0)

        # 멈춰야 할 거리 (사거리 - 오차)
        # 예: 사거리가 60이고 오차가 15면, 45~60 사이에서 멈춘다.
        stop_dist = attack_dist - tol

        # 1) 공격 시도: 충분히 붙었고, 쿨타임도 끝났으면
        # (공격 범위는 무기 리치니까 조금 넉넉해도 됨)
        if dist <= attack_dist and now >= self.next_attack_time:
            if not self._is_in_air():
                self._set_move_dir(0)
                self._tap_attack()
                self.next_attack_time = now + random.uniform(0.7, 1.2)
                return BehaviorTree.SUCCESS

        # 2) 추격 로직 (보정 적용)
        # "사거리보다 멀어?" 가 아니라 "멈춰야 할 거리보다 멀어?"로 체크
        if dist > stop_dist:
            move_dir = 1 if dx > 0 else -1
            self._set_move_dir(move_dir)
        else:
            # 사거리 안쪽(stop_dist 이내)에 안정적으로 들어왔으면 정지
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

            hold_time = seg.jump_template.hold_time if seg.jump_template else 0.5
            is_drop = (hold_time < 0.1)

            if is_drop and not hasattr(seg, 'drop_dir'):
                seg.drop_dir = self._compute_drop_dir(seg, platforms)



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
        # 1. 기본 유효성 검사 (순정 유지)
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

        # [버프 체크]
        now = get_time()
        if isinstance(target, SpeedClockItem) and getattr(me, 'speed_buff_until', 0.0) > now:
            self._reset_item_plan()
            return BehaviorTree.FAIL
        if isinstance(target, AttackClockItem) and getattr(me, 'attack_buff_until', 0.0) > now:
            self._reset_item_plan()
            return BehaviorTree.FAIL


        # 2. 플랜 생성

        if self.item_plan is None:
            print(f"[Item-Nav] New Plan -> ({target.x:.1f}, {target.y:.1f})")
            self.item_plan = scramble_nav.build_scramble_plan_to_point(
                self.stage, me.x, me.y, target.x, target.y
            )
            self.item_segment_index = 0

            # 실패 시 fallback
            if self.item_plan is None or not self.item_plan.segments:
                print("[Item-Nav] Plan Failed. Simple Move.")

                # 실패 카운트 증가
                fail_count = getattr(self, 'item_plan_fail_count', 0) + 1
                self.item_plan_fail_count = fail_count

                # N프레임 이상 계속 실패하면 이 타겟은 포기
                if fail_count > 30:
                    print("[Item-Nav] Plan keeps failing. Drop this item target.")
                    self._reset_item_plan()
                    self.item_target = None
                    self.item_plan_fail_count = 0
                    return BehaviorTree.FAIL

                # 여기서 단순 이동 후 바로 리턴 (중요)
                dx = target.x - me.x
                if abs(dx) > 5.0:
                    self._set_move_dir(1 if dx > 0 else -1)
                else:
                    self._set_move_dir(0)
                return BehaviorTree.RUNNING

        # 3. 도착 확인
        if self.item_segment_index >= len(self.item_plan.segments):
            if abs(me.y - target.y) > 80.0:
                print("[Item-Nav] Height Mismatch at End. Reset.")
                self._reset_item_plan()
                return BehaviorTree.RUNNING

            dx = target.x - me.x
            tol = self._pos_tolerance(base=10.0)
            if abs(dx) > tol:
                self._set_move_dir(1 if dx > 0 else -1)
                return BehaviorTree.RUNNING
            else:
                self._set_move_dir(0)
                return BehaviorTree.SUCCESS

        # 4. 세그먼트 실행
        seg = self.item_plan.segments[self.item_segment_index]
        platforms = scramble_nav.build_platforms_from_stage(self.stage)

        # [A] 걷기 (Walk)
        if seg.kind == 'walk':
            dist = seg.target_x - me.x
            tol = self._pos_tolerance(base=10.0)
            if abs(dist) <= tol:
                self._set_move_dir(0)
                self.item_segment_index += 1
            else:
                self._set_move_dir(1 if dist > 0 else -1)
            return BehaviorTree.RUNNING

        # [B] 점프/하강 (Jump)
        elif seg.kind == 'jump':

            # --- 공통 데이터 준비 ---
            dest_plat_name = seg.jump_template.to_platform
            dest_plat = platforms.get(dest_plat_name)

            # 하강(Drop) 판별: hold_time이 매우 짧으면 하강으로 간주
            hold_time = seg.jump_template.hold_time if seg.jump_template else 0.5
            is_drop = (hold_time < 0.1)


            # drop 세그먼트라면, 이 세그먼트 동안 쓸 가로 방향을 미리 계산해서 저장
            if is_drop and not hasattr(seg, 'drop_dir'):
                seg.drop_dir = self._compute_drop_dir(seg, platforms)

            # 착지 기준 플랫폼 결정
            floor_plat = platforms.get('floor')
            if is_drop and floor_plat is not None:
                land_plat = floor_plat  # drop이면 무조건 floor 기준으로 착지 판단
            else:
                land_plat = dest_plat  # 점프면 기존대로 목표 플랫폼 기준

            # --- (1) 착지 확인 (Landing Check) ---
            # 하강이든 점프든, "땅에 닿았고 + 목표 높이 근처"면 성공
            is_falling = getattr(me, 'vy', 0) <= 0
            if not self._is_in_air() and is_falling:
                if land_plat and abs(me.y - land_plat.T) < 60.0:
                    # print(f"[Jump] Landed. Next segment.")
                    self.jump_end_time = 0.0
                    self._send_key(SDLK_KP_1, False)
                    self._set_move_dir(0)
                    self.item_segment_index += 1
                    return BehaviorTree.RUNNING

            # --- (2) 공중 제어 (Air Control) ---
            # 공중에 있거나, 점프 키를 누르고 있는 중이라면
            if self._is_in_air() or (self.jump_end_time > 0 and get_time() < self.jump_end_time):
                if is_drop:
                    # 점프키 끄고, 드랍용 방향으로만 계속 민다
                    self._send_key(SDLK_KP_1, False)
                    drop_dir = getattr(seg, 'drop_dir', self._compute_drop_dir(seg, platforms))
                    self._set_move_dir(drop_dir)
                else:
                    # [점프 중]: 기존 로직 100% 유지 (대각선/수직 분기)
                    is_hard_diagonal = False
                    if seg.jump_template:
                        fp, tp = seg.jump_template.from_platform, seg.jump_template.to_platform
                        if (fp, tp) in (('r3_L2', 'r2_L'), ('r3_R1', 'r2_R')):
                            is_hard_diagonal = True

                    if is_hard_diagonal:
                        self._set_move_dir(seg.dir)
                        self._send_key(SDLK_KP_1, True)
                        self.jump_end_time = get_time() + 0.1
                    else:
                        target_height = dest_plat.T if dest_plat else (me.y + 100.0)
                        if me.y < target_height + 80.0:
                            self._set_move_dir(0)
                            self._send_key(SDLK_KP_1, True)
                            self.jump_end_time = get_time() + 0.1
                        else:
                            self._set_move_dir(seg.dir)
                return BehaviorTree.RUNNING

            # --- (3) 지상 이동 및 발사 (On Ground Decision) ---
            # 여기가 핵심입니다. Drop과 Jump를 완전히 분리합니다.

            if is_drop:
                # [CASE: 하강]
                # 발사대 범위 같은 건 무시하고, 이 세그먼트의 drop_dir 방향으로만 걷게 한다.
                drop_dir = getattr(seg, 'drop_dir', self._compute_drop_dir(seg, platforms))
                self._set_move_dir(drop_dir)
                # 점프 키는 절대 누르지 않는다. 그냥 걸어가다가 바닥이 사라지면 중력으로 떨어짐.
                return BehaviorTree.RUNNING

            else:
                # [CASE: 점프] - 기존 로직 100% 보존
                # 점프는 '발사대(Takeoff Range)'에 정확히 서는 것이 생명입니다.
                tx1, tx2 = seg.takeoff_range
                margin = self._pos_tolerance(base=5.0)
                ex1 = tx1 - margin
                ex2 = tx2 + margin

                # 발사대 범위 밖이면 -> 범위 안으로 이동
                if not (ex1 <= me.x <= ex2):
                    center = (tx1 + tx2) * 0.5
                    self._set_move_dir(1 if me.x < center else -1)
                    return BehaviorTree.RUNNING

                # 발사대 범위 안이면 -> 멈춰서 점프!
                # print(f"[Jump] Takeoff! Hold:{hold_time:.2f}")
                self._set_move_dir(0)
                self._tap_jump(hold_time)

                # (특수) 대각선 점프는 뛰면서 이동
                if seg.jump_template:
                    fp, tp = seg.jump_template.from_platform, seg.jump_template.to_platform
                    if (fp, tp) in (('r3_L2', 'r2_L'), ('r3_R1', 'r2_R')):
                        self._set_move_dir(seg.dir)

                return BehaviorTree.RUNNING

        return BehaviorTree.RUNNING



    # Action: 플랫폼 네비로 적 추격
    #  - cond_enemy_on_different_platform 이 TRUE 일 때만 호출
    #  - 적이 다른 플랫폼에 올라간 "그 시점의 위치"를 타깃으로 고정
    #  - 그 이후 적이 움직이는 건 고려하지 않음
    def act_chase_enemy_nav(self):
        """플랫폼 네비게이션으로 적 쫓기 (아이템 네비와 거의 같은 패턴)

        - cond_enemy_on_different_platform() 이 먼저 검사된 상태에서만 들어온다고 가정.
        - nav_mode == 'CHASE' 상태일 때만 플랜 유지.
        - 공중에서 새로운 CHASE 시작 금지(_switch_nav_mode가 막아줌).
        - chase_plan / chase_segment_index / chase_target_snapshot 만 사용 (아이템/스크램블과 완전 분리).
        """
        me = self.me
        enemy = self.enemy

        # 0. 기본 방어: 스테이지/적/나 없으면 바로 실패
        if self.stage is None or me is None or enemy is None:
            # 혹시 CHASE 모드로 남아 있으면 정리
            if self.nav_mode == 'CHASE':
                self._switch_nav_mode('NONE')
            return BehaviorTree.FAIL

        now = get_time()

        # 네비 중에는 공격 예약 막기 (아이템 쫓기랑 동일한 안전장치)
        self._suppress_reserved_attack_this_frame()

        # 1. CHASE 모드 진입 시도
        #  - 공중에서는 새로운 네비 시작 금지
        #  - 이미 CHASE라면 그대로 계속 진행
        if self._switch_nav_mode('CHASE') == BehaviorTree.FAIL:
            # 공중에서 모드 전환 시도 등 → 그냥 이번 틱은 네비 안 함
            return BehaviorTree.FAIL

        # 2. 현재 플랫폼 정보 확인
        me_plat = self._get_platform_for(me)
        enemy_plat = self._get_platform_for(enemy)

        # 플랫폼 정보를 못 얻으면 네비 불가 → CHASE 포기
        if me_plat is None or enemy_plat is None:
            self._switch_nav_mode('NONE')
            return BehaviorTree.FAIL

        # 혹시 같은 플랫폼이면 굳이 네비 할 필요 없음 → 성공으로 보고 종료
        if me_plat.name == enemy_plat.name:
            self._switch_nav_mode('NONE')
            return BehaviorTree.SUCCESS

        # 3. 최초 진입: 적 위치 스냅샷 고정
        #    (아이템 쫓을 때 item_target 고정하는 느낌으로)
        if self.chase_target_snapshot is None:
            self.chase_target_snapshot = SimpleNamespace(
                x=enemy.x,
                y=enemy.y,
                platform_name=enemy_plat.name,
                time=now,
            )
            self.chase_plan = None
            self.chase_segment_index = 0
            self.chase_segment_start_time = now

        target = self.chase_target_snapshot

        # 스냅샷이 뭔가 꼬여 있으면 정리 후 실패
        if target is None:
            self._switch_nav_mode('NONE')
            return BehaviorTree.FAIL

        # 4. 플랜이 없으면 한 번만 생성 시도
        if self.chase_plan is None or not getattr(self.chase_plan, 'segments', None):
            plan = scramble_nav.build_scramble_plan_to_point(
                self.stage,
                me.x, me.y,
                target.x, target.y,
            )

            # 4-1. 완전히 플랜 생성 실패 → 간단한 수평 추격 또는 포기
            if (plan is None) or plan.is_empty():
                dx = target.x - me.x
                dy = target.y - me.y
                tol_x = self._pos_tolerance(base=10.0)
                tol_y = 120.0  # 아이템 네비에서 쓰던 정도의 대충 허용치

                # 수직 차이가 크지 않으면, 그냥 수평으로라도 다가가 본다
                if abs(dx) > tol_x and abs(dy) <= tol_y:
                    move_dir = 1 if dx > 0 else -1
                    self._set_move_dir(move_dir)
                    # CHASE 모드는 유지하되, 여전히 네비 중이므로 RUNNING
                    return BehaviorTree.RUNNING

                # 정말로 경로가 안 나온다 → CHASE 포기
                self._set_move_dir(0)
                self._switch_nav_mode('NONE')
                return BehaviorTree.FAIL

            # 4-2. 플랜 생성 성공
            self.chase_plan = plan
            self.chase_segment_index = 0
            self.chase_segment_start_time = now

        # 여기까지 오면 self.chase_plan 은 유효한 ScramblePlan 이라고 가정
        plan = self.chase_plan

        # 5. 플랜 마지막 세그먼트까지 갔는지 체크
        if self.chase_segment_index >= len(plan.segments):
            # 도착했는데, 정말 같은 플랫폼인지 한 번 더 확인
            me_plat = self._get_platform_for(me)
            enemy_plat = self._get_platform_for(enemy)

            if me_plat and enemy_plat and me_plat.name == enemy_plat.name:
                # 같은 플랫폼에 올라왔으면 추격 성공
                self._set_move_dir(0)
                self._switch_nav_mode('NONE')
                # 타겟/플랜도 함께 정리
                self.chase_plan = None
                self.chase_target_snapshot = None
                self.chase_segment_index = 0
                return BehaviorTree.SUCCESS

            # 아직도 다른 플랫폼이라면 → 이 플랜은 더 이상 의미 없다 → 포기
            self._set_move_dir(0)
            self._switch_nav_mode('NONE')
            self.chase_plan = None
            self.chase_target_snapshot = None
            self.chase_segment_index = 0
            return BehaviorTree.FAIL

        # 6. 스턱 타임아웃: 한 세그먼트에서 너무 오래 멈춰 있으면 포기
        if (now - self.chase_segment_start_time) > self.chase_stuck_timeout:
            # 세그먼트가 너무 오래 진행 안 됨 → 플랜 포기
            self._set_move_dir(0)
            self._switch_nav_mode('NONE')
            self.chase_plan = None
            self.chase_target_snapshot = None
            self.chase_segment_index = 0
            return BehaviorTree.FAIL

        # 7. 현재 세그먼트 실행 (아이템 네비와 동일한 패턴)
        seg = plan.segments[self.chase_segment_index]

        # 7-a. walk 세그먼트: target_x 까지 수평 이동
        if seg.kind == 'walk':
            if seg.target_x is None:
                # 방어 코드: target_x 가 없으면 그냥 다음 세그먼트로 넘어간다
                self.chase_segment_index += 1
                self.chase_segment_start_time = now
                return BehaviorTree.RUNNING

            target_x = seg.target_x
            tol = self._pos_tolerance(base=10.0)
            dx = target_x - me.x

            if abs(dx) <= tol:
                # 거의 도착 → 다음 세그먼트로
                self._set_move_dir(0)
                self.chase_segment_index += 1
                self.chase_segment_start_time = now
            else:
                move_dir = 1 if dx > 0 else -1
                self._set_move_dir(move_dir)

            return BehaviorTree.RUNNING

        # 7-b. jump 세그먼트: 아이템 네비와 최대한 같은 패턴
        if seg.kind == 'jump':
            # 발사 구간 설정
            if seg.takeoff_range:
                tx1, tx2 = seg.takeoff_range
                takeoff_mid = 0.5 * (tx1 + tx2)
            else:
                tx1 = tx2 = takeoff_mid = me.x

            tol = self._pos_tolerance(base=5.0)

            # "점프 키 누르고 있는 중" 판정 (아이템 네비와 동일한 패턴)
            jumping_now = (self.jump_end_time > 0.0 and now < self.jump_end_time)

            # (1) 아직 점프 전: 지상 + 점프 키 안 누른 상태
            if (not self._is_in_air()) and (not jumping_now):
                # 발사 위치까지 수평 이동
                if me.x < tx1 - tol:
                    self._set_move_dir(1)
                    return BehaviorTree.RUNNING
                if me.x > tx2 + tol:
                    self._set_move_dir(-1)
                    return BehaviorTree.RUNNING

                # takeoff_range 안에 들어왔다 → 점프 시작
                hold = getattr(seg.jump_template, 'hold_time', 0.5) if seg.jump_template else 0.5

                # drop 전용 템플릿(hold_time <= 0)은 점프 키 안 쓰고 그냥 떨어지게 둔다
                if hold > 0.0:
                    self._tap_jump(hold_duration=hold)

                # 점프/드롭 중에는 템플릿이 정한 dir 방향으로 밀어준다
                self._set_move_dir(seg.dir or 0)
                return BehaviorTree.RUNNING

            # (2) 점프/드롭 중: 수평 방향 고정
            if self._is_in_air() or jumping_now:
                self._set_move_dir(seg.dir or 0)
                return BehaviorTree.RUNNING

            # (3) 여기까지 왔다는 건 방금 착지했다는 뜻 → 다음 세그먼트로
            self._set_move_dir(0)
            self.chase_segment_index += 1
            self.chase_segment_start_time = now
            return BehaviorTree.RUNNING

        # 7-c. 알 수 없는 kind → 방어 코드: 그냥 다음 세그먼트로 넘긴다
        self.chase_segment_index += 1
        self.chase_segment_start_time = now
        return BehaviorTree.RUNNING