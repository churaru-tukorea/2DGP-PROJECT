from pico2d import *
import logo_mode
import game_framework
import play_mode as start_mode
#이건 타이틀 모드를 스타트 모드라고 간주할 수 있다.

open_canvas()
game_framework.run(start_mode)
close_canvas()