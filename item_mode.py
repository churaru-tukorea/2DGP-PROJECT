# item_mode.py
from pico2d import *
import game_framework
import config

image = None  # 나중에 패널/이미지 넣을 자리

def init():
    global image
    image = None
    print('[item_mode] init - "-"=sword, "="+spear 선택')

def finish():
    global image
    image = None

def pause():
    pass

def resume():
    pass

def update():
    pass

def draw():
    clear_canvas()
    # 무기 선택같은건 나중에 추가하자.
    update_canvas()

def handle_events():
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            game_framework.quit()

        elif event.type == SDL_KEYDOWN:
            # ESC : 타이틀로 돌아가기
            if event.key == SDLK_ESCAPE:
                import title_mode
                game_framework.change_mode(title_mode)

            # '-' 또는 키패드 '-' -> 칼 모드
            elif event.key in (SDLK_MINUS, SDLK_KP_MINUS):
                import play_mode
                config.weapon_mode = 'sword'
                print('[item_mode] weapon_mode = sword')
                game_framework.change_mode(play_mode)

            # '='(Shift 누르면 화면상 +) 또는 키패드 '+' -> 창 모드
            elif event.key in (SDLK_EQUALS, SDLK_KP_PLUS):
                import play_mode
                config.weapon_mode = 'spear'
                print('[item_mode] weapon_mode = spear')
                game_framework.change_mode(play_mode)
