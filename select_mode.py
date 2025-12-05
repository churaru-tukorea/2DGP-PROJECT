from pico2d import *
import game_framework
import config

image = None


def init():
    global image
    image = load_image('select.png')


def finish():
    global image
    if image is not None:
        del image
        image = None


def pause():
    pass


def resume():
    pass


def update():
    pass


def draw():
    clear_canvas()
    # 이미지 정 가운데(1280x720 기준)
    image.draw(640, 360)
    update_canvas()


def handle_events():
    from sdl2 import SDLK_COMMA, SDLK_PERIOD  # ,  .  키 (Shift 누르면 < >)

    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            game_framework.quit()

        elif event.type == SDL_KEYDOWN:
            # ESC : 타이틀로 돌아가기
            if event.key == SDLK_ESCAPE:
                import title_mode
                game_framework.change_mode(title_mode)

            # '<' 키 (실제로는 COMMA + Shift) → CPU 모드
            elif event.key == SDLK_COMMA:
                import play_mode
                config.player2_mode = 'cpu'
                print('[select_mode] player2_mode = cpu')
                game_framework.change_mode(play_mode)

            # '>' 키 (실제로는 PERIOD + Shift) → 2인 플레이 모드
            elif event.key == SDLK_PERIOD:
                import play_mode
                config.player2_mode = '2p'
                print('[select_mode] player2_mode = 2p')
                game_framework.change_mode(play_mode)