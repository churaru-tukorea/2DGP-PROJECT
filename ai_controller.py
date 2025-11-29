from types import SimpleNamespace
import random

from pico2d import SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT, SDLK_KP_1, get_time

from behavior_tree import BehaviorTree, Selector, Action
