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
            p1.handle_event(event)#그냥 둘다 한번씩 처리하면 되지 않을까?
            p2.handle_event(event)





def init():

    global p1
    global p2
    global running
    global sword


    running = True


    p1 = Character(pid=1)
    p1.x = 300
    p2 = Character(pid=2)
    p2.x = 900



    grass = Grass()
    game_world.add_object(grass, 0)

    game_world.add_object(p1, 1)
    game_world.add_object(p2, 1)

    sword = Sword(0)
    game_world.add_object(sword, 1)

#플레이어가 검을 먹는 그걸 하려고.
    game_world.add_collision_pair('char:sword', p1, None)
    game_world.add_collision_pair('char:sword', p2, None)
    game_world.add_collision_pair('char:sword', None, sword)






def update():
    game_world.update()
    game_world.handle_collisions()



def draw():
    clear_canvas()
    game_world.render()
    update_canvas()

def finish():
    pass





