
from sprite_tuples import ACTION, sprite

LEFT_FLIP_RULE = 'ADD_PI'
PIVOT_FROM_CENTER_PX = (-1.0, 12.0)  # 손잡이 끝

POSE = {
    'idle': [{'offset_src_px': (19.47, 7.07), 'deg': -30.0}, {'offset_src_px': (19.47, 7.07), 'deg': -30.0}],
    'move': [{'offset_src_px': (3.75, 9.81), 'deg': 80.0}, {'offset_src_px': (4.79, 7.86), 'deg': 85.0},
             {'offset_src_px': (5.86, 6.86), 'deg': 90.0}, {'offset_src_px': (7.00, 8.22), 'deg': 95.0},
             {'offset_src_px': (9.0, 8.04), 'deg': 100.0}, {'offset_src_px': (11.83, 6.42), 'deg': 110.0},
             {'offset_src_px': (9.0, 6.67), 'deg': 100.0}, {'offset_src_px': (7.00, 6.58), 'deg': 95.0},
             {'offset_src_px': (5.86, 7.38), 'deg': 90.0}, {'offset_src_px': (4.79, 7.92), 'deg': 85.0}],
    'attack_fire': [{'offset_src_px': (21.45, 8.82), 'deg': 30.0},
                    {'offset_src_px': (18.27, 9.47), 'deg': 30.0},
                    {'offset_src_px': (18.5, 8.44), 'deg': 30.0},
                    {'offset_src_px': (20.5, 8.44), 'deg': 30.0},
                    {'offset_src_px': (23.93, 14.47), 'deg': 30.0},
                    {'offset_src_px': (17.67, 8.67), 'deg': 30.0},
                    {'offset_src_px': (17.67, 8.67), 'deg': 30.0}],
}