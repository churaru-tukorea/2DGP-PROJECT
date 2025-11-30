"""

검/창 쟁탈전을 위한 네비게이션(무기 추적) 설계용 모듈 초안.

핵심 아이디어
-------------
- 스테이지를 "플랫폼 단위"로 보고, 각 플랫폼을 이름으로 구분한다. (floor, r3_L2, r2_L, mid_top 등)
- 플랫폼 사이의 점프 가능성을 `JumpTemplate`로 정의한다.
  - from_platform, to_platform
  - 이 플랫폼 위에서 어느 구간에서 점프하면(takeoff_range_ratio)
  - 위 플랫폼의 어느 구간에 착지하는지(landing_range_ratio)
  - 점프 중에는 어느 방향 키를 얼마나 홀드해야 하는지(dir, hold_time)
- ScramblePhase에서는
  1) 현재 내 위치 / 무기 위치가 올라가 있는 플랫폼을 찾고
  2) 플랫폼 그래프 위에서 start → target 경로를 찾은 뒤
  3) 그 경로를 "walk/jump 세그먼트" 시퀀스로 풀어낸다.

여기서는 "구조 + 데이터 스켈레톤"만 잡고,
 ratio·시간 값은 대략적인 초안만 넣어둔다.
 실제 튜닝은 캐릭터 점프력에 맞춰 수동으로 조정하면 된다.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Iterable
from collections import deque


# ---------------------------------------------------------------------------
# 1. 기본 자료 구조 (클래스 정의)
# ---------------------------------------------------------------------------

@dataclass
class PlatformDef:
    """화면상의 플랫폼 박스 정보"""
    name: str
    L: float
    B: float
    R: float
    T: float

    @property
    def width(self) -> float:
        return self.R - self.L

    def x_from_ratio(self, ratio: float) -> float:
        """비율(0.0~1.0)을 x좌표로 변환"""
        return self.L + self.width * ratio

    def clamp_x(self, x: float, margin: float = 20.0) -> float:
        """플랫폼 밖으로 나가지 않도록 좌표 보정"""
        return max(self.L + margin, min(self.R - margin, x))


@dataclass
class JumpTemplate:
    """점프 동작 정의 (어디서, 어떻게 점프할지)"""
    name: str
    from_platform: str
    to_platform: str
    # 0.0 ~ 1.0 비율 범위 (출발 플랫폼 기준)
    takeoff_min_ratio: float
    takeoff_max_ratio: float
    # 0.0 ~ 1.0 비율 범위 (도착 플랫폼 기준)
    landing_min_ratio: float
    landing_max_ratio: float
    dir: int  # -1(왼쪽), 0(수직), 1(오른쪽)
    hold_time: float  # 점프/방향키 유지 시간


@dataclass
class ScrambleSegment:
    """경로의 한 단계 (걷기 또는 점프)"""
    kind: str  # "walk" or "jump"
    platform: str
    target_x: Optional[float] = None
    dir: int = 0
    jump_template: Optional[JumpTemplate] = None
    takeoff_range: Optional[Tuple[float, float]] = None
    landing_range: Optional[Tuple[float, float]] = None


@dataclass
class ScramblePlan:
    """완성된 전체 이동 계획"""
    segments: List[ScrambleSegment]
    start_platform: str
    target_platform: str

    def is_empty(self) -> bool:
        return not self.segments


# ---------------------------------------------------------------------------
# 2. 플랫폼 파싱 및 유틸 함수
# ---------------------------------------------------------------------------

IGNORED_PLATFORMS = {"ceiling", "left_wall", "right_wall"}


def build_platforms_from_stage(stage_colliders) -> Dict[str, PlatformDef]:
    """StageColliders에서 플랫폼 정보를 추출"""
    platforms: Dict[str, PlatformDef] = {}
    # stage_colliders.get_screen_boxes()가 (name, typ, L, B, R, T) 튜플 리스트를 반환한다고 가정
    for name, typ, L, B, R, T in stage_colliders.get_screen_boxes():
        if typ != "SOLID": continue
        if name in IGNORED_PLATFORMS: continue
        platforms[name] = PlatformDef(name, L, B, R, T)
    return platforms


def find_platform_under_point(
        platforms: Dict[str, PlatformDef],
        x: float,
        y: float,
        vertical_tolerance: float = 90.0,
) -> Optional[PlatformDef]:
    """특정 좌표(x,y)가 밟고 있는 플랫폼 찾기"""
    best: Optional[PlatformDef] = None
    best_dy = 1e9

    # 가장자리 인식을 위해 x축 여유를 10픽셀 정도 줌
    margin_x = 10.0

    for plat in platforms.values():
        # x좌표가 플랫폼 범위 안(여유폭 포함)에 있는지
        if not (plat.L - margin_x <= x <= plat.R + margin_x):
            continue

        # y좌표(발 위치)가 플랫폼 상단 근처인지
        # (캐릭터 y는 중심이므로, 발바닥 보정 없이 들어온다면 오차가 클 수 있음.
        # 보통 입력 y는 캐릭터 중심이므로, 플랫폼 T보다 위/아래 검사)
        dy = abs(y - plat.T)

        if dy <= vertical_tolerance and dy < best_dy:
            best_dy = dy
            best = plat

    return best



JUMP_TEMPLATES: List[JumpTemplate] = [
    # ==========================================================
    # 1. 바닥(Floor) -> 1층 구석 (r3_L1, r3_R2) [수정됨]
    # 전략: 너무 중앙까지 가지 말고, 플랫폼 바로 옆(Gap)에서 뛴다.
    # ==========================================================

    # [Left] 바닥 -> r3_L1 (왼쪽 구석)
    # r3_L1이 대략 0.2에서 끝나므로, 0.22~0.26(바로 옆)에서 뜀
    JumpTemplate("floor_to_r3_L1_side", "floor", "r3_L1",
                 0.12, 0.16,  # 플랫폼 바로 오른쪽 옆
                 0.5, 0.9,
                 -1,  # 왼쪽으로 점프
                 0.5),

    # [Right] 바닥 -> r3_R2 (오른쪽 구석)
    # r3_R2가 대략 0.8에서 시작하므로, 0.74~0.78(바로 옆)에서 뜀
    JumpTemplate("floor_to_r3_R2_side", "floor", "r3_R2",
                 0.84, 0.88,  # 플랫폼 바로 왼쪽 옆
                 0.1, 0.5,
                 +1,  # 오른쪽으로 점프
                 0.5),

    # ==========================================================
    # 2. 바닥(Floor) -> 1층 중앙 (r3_L2, r3_R1) [기존 유지]
    # 여기는 중앙에서 뛰는 게 맞음
    # ==========================================================
    JumpTemplate("floor_to_r3_L2_center_entry", "floor", "r3_L2",
                 0.45, 0.48, 0.6, 0.9, -1, 0.5),

    JumpTemplate("floor_to_r3_R1_center_entry", "floor", "r3_R1",
                 0.52, 0.55, 0.1, 0.4, +1, 0.5),

    # ==========================================================
    # 3. 1층 플랫폼 간 이동 (징검다리) [기존 유지]
    # ==========================================================
    JumpTemplate("r3_L1_to_r3_L2", "r3_L1", "r3_L2", 0.80, 0.95, 0.05, 0.20, +1, 0.4),
    JumpTemplate("r3_L2_to_r3_L1", "r3_L2", "r3_L1", 0.05, 0.20, 0.80, 0.95, -1, 0.4),
    JumpTemplate("r3_R2_to_r3_R1", "r3_R2", "r3_R1", 0.05, 0.20, 0.80, 0.95, -1, 0.4),
    JumpTemplate("r3_R1_to_r3_R2", "r3_R1", "r3_R2", 0.80, 0.95, 0.05, 0.20, +1, 0.4),

    # ==========================================================
    # 4. 1층 -> 2층 (High Platforms) [기존 유지]
    # ==========================================================
    # r3_L2 -> r2_L : 왼쪽 위로 대각선 점프
    # - r3_L2의 "왼쪽 10~25%" 지점에서 뜀
    # - r2_L의 "오른쪽 60~90%" 영역에 착지
    JumpTemplate("r3_L2_to_r2_L_diag", "r3_L2", "r2_L",
                 0.10, 0.25,  # takeoff_min_ratio, takeoff_max_ratio
                 0.6, 0.9,  # landing_min_ratio, landing_max_ratio
                 -1,  # 왼쪽으로 이동
                 0.6),  # 점프 키 홀드 시간(최대 점프)

    # r3_R1 -> r2_R : 오른쪽 위로 대각선 점프
    # - r3_R1의 "오른쪽 75~90%" 지점에서 뜀
    # - r2_R의 "왼쪽 10~40%" 영역에 착지
    JumpTemplate("r3_R1_to_r2_R_diag", "r3_R1", "r2_R",
                 0.75, 0.90,  # r3_R1 오른쪽 끝 쪽에서 출발
                 0.1, 0.4,  # r2_R 왼쪽 절반으로 착지
                 +1,  # 오른쪽으로 이동
                 0.6),

    # ==========================================================
    # 5. 2층 -> 3층 & 하강 [기존 유지]
    # ==========================================================
    JumpTemplate("r2_L_to_mid_top", "r2_L", "mid_top", 0.7, 0.95, 0.1, 0.4, +1, 0.45),
    JumpTemplate("r2_R_to_mid_top", "r2_R", "mid_top", 0.05, 0.3, 0.6, 0.9, -1, 0.45),

    JumpTemplate("drop_mid_to_r2_L", "mid_top", "r2_L", 0.0, 0.3, 0.6, 0.9, -1, 0.0),
    JumpTemplate("drop_mid_to_r2_R", "mid_top", "r2_R", 0.7, 1.0, 0.1, 0.4, +1, 0.0),
    JumpTemplate("drop_r2_L_to_r3_L2", "r2_L", "r3_L2", 0.5, 0.9, 0.4, 0.8, 0, 0.0),
    JumpTemplate("drop_r2_R_to_r3_R1", "r2_R", "r3_R1", 0.1, 0.5, 0.2, 0.6, 0, 0.0),
    JumpTemplate("drop_r3_L2_to_floor", "r3_L2", "floor", 0.0, 1.0, 0.35, 0.45, 0, 0.0),
    JumpTemplate("drop_r3_R1_to_floor", "r3_R1", "floor", 0.0, 1.0, 0.55, 0.65, 0, 0.0),
    JumpTemplate("drop_r3_L1_to_floor", "r3_L1", "floor", 0.0, 1.0, 0.1, 0.15, 0, 0.0),
    JumpTemplate("drop_r3_R2_to_floor", "r3_R2", "floor", 0.0, 1.0, 0.85, 0.9, 0, 0.0),
]

# ---------------------------------------------------------------------------
# 4. 경로 탐색 및 계획 수립
# ---------------------------------------------------------------------------

def build_jump_adjacency(templates: Iterable[JumpTemplate]) -> Dict[str, List[JumpTemplate]]:
    """플랫폼 연결 정보 생성"""
    adj: Dict[str, List[JumpTemplate]] = {}
    for jt in templates:
        adj.setdefault(jt.from_platform, []).append(jt)
    return adj


def find_platform_path(
        start: PlatformDef,
        target: PlatformDef,
        templates: Iterable[JumpTemplate] = JUMP_TEMPLATES,
) -> Optional[List[str]]:
    """BFS로 최단 플랫폼 경로(이름 리스트)를 찾는다."""
    if start.name == target.name:
        return [start.name]

    adj = build_jump_adjacency(templates)

    q = deque([start.name])
    visited = {start.name}
    parent = {start.name: None}

    found = False
    while q:
        curr = q.popleft()
        if curr == target.name:
            found = True
            break

        # 현재 플랫폼에서 갈 수 있는 모든 다음 플랫폼 수집
        neighbors = set()
        for jt in adj.get(curr, []):
            neighbors.add(jt.to_platform)

        for nxt in neighbors:
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = curr
                q.append(nxt)

    if not found:
        return None

    # 역추적
    path = []
    curr = target.name
    while curr is not None:
        path.append(curr)
        curr = parent[curr]

    path.reverse()
    return path


def _pick_best_jump(
        from_plat_name: str,
        to_plat_name: str,
        current_x: float,
        platforms: Dict[str, PlatformDef],
        templates: Iterable[JumpTemplate]
) -> Optional[JumpTemplate]:
    """현재 내 위치(current_x)에서 가장 가까운 점프대를 선택"""
    candidates = [
        jt for jt in templates
        if jt.from_platform == from_plat_name and jt.to_platform == to_plat_name
    ]

    if not candidates:
        return None

    best_jt = None
    min_dist = 1e9

    from_def = platforms[from_plat_name]

    for jt in candidates:
        # 점프 시작 구간의 중심점
        tko_center_ratio = (jt.takeoff_min_ratio + jt.takeoff_max_ratio) * 0.5
        tko_x = from_def.x_from_ratio(tko_center_ratio)

        dist = abs(current_x - tko_x)
        if dist < min_dist:
            min_dist = dist
            best_jt = jt

    return best_jt


def _make_ranges(jt: JumpTemplate, platforms: Dict[str, PlatformDef]):
    f = platforms[jt.from_platform]
    t = platforms[jt.to_platform]
    return (
        (f.x_from_ratio(jt.takeoff_min_ratio), f.x_from_ratio(jt.takeoff_max_ratio)),
        (t.x_from_ratio(jt.landing_min_ratio), t.x_from_ratio(jt.landing_max_ratio))
    )


# [scramble_nav.py] build_scramble_plan_to_point 함수 전체 교체

def build_scramble_plan_to_point(
        stage_colliders,
        me_x: float, me_y: float,
        target_x: float, target_y: float
) -> Optional[ScramblePlan]:
    """현재 위치에서 목표 지점까지의 ScramblePlan 생성 (안정화 버전)"""

    platforms = build_platforms_from_stage(stage_colliders)

    # ---------------------------------------------------------
    # 1. 내 위치 & 목표 위치 찾기 (Probe: 좌우 30px 탐색)
    # ---------------------------------------------------------
    def _find_robust(x, y):
        p = find_platform_under_point(platforms, x, y)
        if p: return p
        p = find_platform_under_point(platforms, x - 30, y)
        if p: return p
        p = find_platform_under_point(platforms, x + 30, y)
        return p

    start_plat = _find_robust(me_x, me_y)
    target_plat = _find_robust(target_x, target_y)

    # ---------------------------------------------------------
    # [안정화 핵심 1] 플랫폼을 못 찾았더라도, 거리가 가까우면(150px 이내)
    # "같은 층에 있다"고 가정하고 무조건 걷기 경로를 생성한다. (Blind Walk)
    # -> 1층 구석이나 모서리에서 칼 못 줍는 버그 원천 차단
    # ---------------------------------------------------------
    dist_x = abs(target_x - me_x)
    dist_y = abs(target_y - me_y)

    if (start_plat is None or target_plat is None):
        if dist_x < 200.0 and dist_y < 80.0:
            # 플랫폼 이름은 모르겠지만 일단 걸어가라
            dummy_name = start_plat.name if start_plat else "unknown"
            # 가상의 세그먼트 생성
            seg = ScrambleSegment("walk", dummy_name, target_x=target_x)
            return ScramblePlan([seg], dummy_name, dummy_name)

    # 그래도 없으면 진짜 경로 불가
    if start_plat is None or target_plat is None:
        return None

    # ---------------------------------------------------------
    # [안정화 핵심 2] 같은 플랫폼이면 높이 검사고 뭐고 무조건 걷기
    # ---------------------------------------------------------
    if start_plat.name == target_plat.name:
        segments = []
        # clamp_x를 쓰되, 목표가 플랫폼 살짝 밖이어도 갈 수 있게 처리
        safe_target_x = start_plat.clamp_x(target_x, margin=0.0)
        segments.append(ScrambleSegment("walk", start_plat.name, target_x=safe_target_x))
        return ScramblePlan(segments, start_plat.name, target_plat.name)

    # ---------------------------------------------------------
    # 3. 경로 탐색 (점프가 필요한 경우)
    # ---------------------------------------------------------
    path_names = find_platform_path(start_plat, target_plat, JUMP_TEMPLATES)
    if path_names is None:
        return None

    segments = []
    curr_x_cursor = me_x

    for i in range(len(path_names) - 1):
        curr_name = path_names[i]
        next_name = path_names[i + 1]

        best_jt = _pick_best_jump(curr_name, next_name, curr_x_cursor, platforms, JUMP_TEMPLATES)
        if best_jt is None: return None

        tko_range, lnd_range = _make_ranges(best_jt, platforms)

        # ==========================================================
        # [수정] 발사대(takeoff) 좌표가 플랫폼 밖으로 나가지 않게 '꽉' 잡기(Clamp)
        # ==========================================================
        curr_plat_def = platforms[curr_name]

        # 1. 튜플을 리스트로 풀어서 수정 가능하게 만듦
        tx1, tx2 = tko_range

        # 2. 플랫폼 왼쪽/오른쪽 끝에서 20픽셀 정도 안쪽으로 강제 이동
        safe_margin = 20.0
        safe_min = curr_plat_def.L + safe_margin
        safe_max = curr_plat_def.R - safe_margin

        # 3. 범위 자체가 안전 구역 안에 들어오도록 보정
        tx1 = max(safe_min, min(safe_max, tx1))
        tx2 = max(safe_min, min(safe_max, tx2))

        # (혹시 범위가 뒤집혔으면 중앙값으로 통일)
        if tx1 > tx2:
            tx1 = tx2 = (tx1 + tx2) / 2

        tko_range = (tx1, tx2)  # 다시 튜플로 포장
        # ==========================================================

        tko_center = (tko_range[0] + tko_range[1]) * 0.5

        # Walk 세그먼트 추가
        segments.append(ScrambleSegment(
            kind="walk",
            platform=curr_name,
            # 걷기 목표도 안전하게 clamp된 tko_center를 사용
            target_x=tko_center
        ))

        # Jump 세그먼트 추가
        segments.append(ScrambleSegment(
            kind="jump",
            platform=curr_name,
            jump_template=best_jt,
            takeoff_range=tko_range,  # 보정된 범위 사용
            landing_range=lnd_range,
            dir=best_jt.dir
        ))

        lnd_center = (lnd_range[0] + lnd_range[1]) * 0.5
        curr_x_cursor = lnd_center

    last_plat = platforms[target_plat.name]
    segments.append(ScrambleSegment(
        kind="walk",
        platform=last_plat.name,
        target_x=last_plat.clamp_x(target_x)
    ))

    print(f"\n[NAV-GEN] Start: {start_plat.name} -> Target: {target_plat.name}")
    if segments:
        for i, s in enumerate(segments):
            if s.kind == 'walk':
                print(f"  [{i}] WALK on {s.platform} -> Go to X={s.target_x:.1f}")
            elif s.kind == 'jump':
                print(f"  [{i}] JUMP from {s.platform} -> {s.jump_template.to_platform}")
                print(f"       Takeoff Range: {s.takeoff_range}")
    else:
        print("  [NAV-GEN] FAILED: Segments list is empty!")

    return ScramblePlan(segments, start_plat.name, target_plat.name)