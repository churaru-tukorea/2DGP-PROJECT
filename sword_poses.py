
from sprite_tuples import ACTION, sprite

LEFT_FLIP_RULE = 'NEGATE'
PIVOT_FROM_CENTER_PX = (-1.0, 12.0)  # 손잡이 끝

POSE = {
    'idle': [{'offset_src_px': (19.47, 7.07), 'deg': -30.0}, {'offset_src_px': (19.47, 7.07), 'deg': -30.0}],
    'move': [{'offset_src_px': (3.75, 9.81), 'deg': 40.0}, {'offset_src_px': (4.79, 7.86), 'deg': 35.0},
             {'offset_src_px': (5.86, 6.86), 'deg': 30.0}, {'offset_src_px': (7.00, 8.22), 'deg': 25.0},
             {'offset_src_px': (9.0, 8.04), 'deg': 20.0}, {'offset_src_px': (11.83, 6.42), 'deg': 10.0},
             {'offset_src_px': (9.0, 6.67), 'deg': 20.0}, {'offset_src_px': (7.00, 6.58), 'deg': 25.0},
             {'offset_src_px': (5.86, 7.38), 'deg': 30.0}, {'offset_src_px': (4.79, 7.92), 'deg': 35.0}],
    'attack_fire': [{'offset_src_px': (3.45, 6.82), 'deg': 140.0},
                    {'offset_src_px': (7.27, 4.47), 'deg': 160.0},
                    {'offset_src_px': (10.5, 5.44), 'deg': 180.0},
                    {'offset_src_px': (15.5, 5.44), 'deg': 210.0},
                    {'offset_src_px': (21.93, 15.47), 'deg': 230.0},
                    {'offset_src_px': (15.67, 18.67), 'deg': 265.0},
                    {'offset_src_px': (13.67, 18.67), 'deg': 300.0}],
    'parry_hold': [{'offset_src_px': (20.47, 7.07), 'deg': 0.0}]
}