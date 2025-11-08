
from sprite_tuples import ACTION, sprite

LEFT_FLIP_RULE = 'ADD_PI'        # 'NEGATE' | 'KEEP' | 'ADD_PI' 중 선택
PIVOT_FROM_CENTER_PX = (-1.0, -13.5)  # real_sword(15x31) 기준 손잡이 위치(센터 기준 px)

def _len(action_name: str) -> int:
    return len(sprite[ACTION[action_name]])

def _empty(action_name: str):
    return [None] * _len(action_name)

POSE = {
    'idle':        _empty('idle'),        # 2프
    'move':        _empty('move'),        # 10프
    'attack_fire': _empty('attack_fire'), # 7프
}

# ====== 예시(샘플) ======
# idle 0,1 프레임에 동일 값 사용 예시 — 네가 직접 측정해서 숫자만 바꾸면 됨
POSE['idle'][0] = {'offset_src_px': (14, 29), 'deg': -25}
POSE['idle'][1] = {'offset_src_px': (14, 29), 'deg': -25}

# 사용법: POSE['attack_fire'][0] = {'offset_src_px': (16, 27), 'deg': -60}
# 없는 프레임(None)은 검을 안 그림