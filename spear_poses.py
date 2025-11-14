# spear_poses.py
from sprite_tuples import ACTION, sprite

# 칼이랑 동일하게: 왼쪽일 때 각도 부호 뒤집기
LEFT_FLIP_RULE = 'NEGATE'
# 무기 이미지 중심 기준, 손잡이 끝까지의 오프셋 (px) – sword와 동일로 시작
PIVOT_FROM_CENTER_PX = (-1.0, -100.0)

POSE = {
    # idle / move / parry_hold 는 일단 sword 기준 복사
    'idle': [
        {'offset_src_px': (18.47, 7.07), 'deg': -10.0},
        {'offset_src_px': (18.47, 7.07), 'deg': -10.0},
    ],

    'move': [
        {'offset_src_px': (3.75, 9.81), 'deg': 40.0},
        {'offset_src_px': (4.79, 7.86), 'deg': 35.0},
        {'offset_src_px': (5.86, 6.86), 'deg': 30.0},
        {'offset_src_px': (7.00, 8.22), 'deg': 25.0},
        {'offset_src_px': (9.0,  8.04), 'deg': 20.0},
        {'offset_src_px': (11.83, 6.42), 'deg': 10.0},
        {'offset_src_px': (9.0,  6.67), 'deg': 20.0},
        {'offset_src_px': (7.00, 6.58), 'deg': 25.0},
        {'offset_src_px': (5.86, 7.38), 'deg': 30.0},
        {'offset_src_px': (4.79, 7.92), 'deg': 35.0},
    ],

    # ★ 창 던지기 포즈 – 7프레임 (attack_spear 0~6)
    'attack_spear': [
        # 0: 옆에서 들고 있는 자세 (조금 위쪽)
        {'offset_src_px': (4.0,  10.0),  'deg': -60.0},
        # 1: 어깨 쪽으로 올리는 중
        {'offset_src_px': (3.0,  10.5),  'deg': -55.0},
        # 2: 머리 위 근처
        {'offset_src_px': (2.5, 12.0),  'deg': -40.0},
        # 3: 뒤로 젖히며 최대 장전
        {'offset_src_px': (8.0, 12.0),  'deg': -45.0},
        # 4: 앞으로 던지기 시작
        {'offset_src_px': (13.0, 11.0),  'deg': -50.0},
        # 5: 완전히 앞으로 뻗어서 던진 포즈
        {'offset_src_px': (18.0, 12.5),  'deg': -50.0},
        # 6: 팔이 살짝 내려오며 후딜
        {'offset_src_px': (17.0, 13.0), 'deg': -50.0},
    ],

    'parry_hold': [
        {'offset_src_px': (20.47, 7.07), 'deg': 0.0},
    ],
}
