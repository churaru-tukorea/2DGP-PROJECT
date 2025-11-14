import random, math
from pico2d import load_image, get_canvas_width, get_time, draw_rectangle
import game_world, game_framework
from spear_poses import POSE, LEFT_FLIP_RULE, PIVOT_FROM_CENTER_PX

class Spear:
    def __init__(self, ground_y: int, x: int | None = None):
        pass
    def attach_to(self, owner):
        pass

    def detach(self):
        pass
#던져지는
    def throw_from_owner(self):
        pass
#검처럼 땅에 랜덤하게 박히는
    def reset_to_ground_random(self):
        pass
    def update(self):
        pass
    def draw(self):
        pass
    def get_bb(self):
        pass
    def get_obb(self):
        pass
    def _compute_equipped_pose(self):
        pass




