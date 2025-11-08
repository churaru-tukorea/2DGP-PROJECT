from pico2d import *
from character import Character
import game_world
from grass import Grass
from sword import Sword

running = True
character = None


def handle_events():
    global running

    event_list = get_events()
    for event in event_list:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
        else:
            character.handle_event(event)  # space 키가 들어오면 소년에게 전달.





def init():

    global character
    global running
    global sword


    running = True


    sword = Sword(0)
    game_world.add_object(sword, 0)

    grass = Grass()
    game_world.add_object(grass, 0)

    character = Character()
    game_world.add_object(character, 1)




def update():
    game_world.update()



def draw():
    clear_canvas()
    game_world.render()
    update_canvas()

def finish():
    pass





