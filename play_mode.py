from pico2d import *
from character import Character
import game_world
from grass import Grass
from sword import Sword

from static_image_layer import StaticImageLayer
from stage_colliders import StageColliders


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

    background_layer = StaticImageLayer('background.png', fit='cover')
    game_world.add_object(background_layer, 0)

    boss_stage_layer = StaticImageLayer('boss stage.png', fit='cover') # 혹은 'boss_stage.png'
    game_world.add_object(boss_stage_layer, 1)

    stage_colliders = StageColliders(boss_stage_layer, debug=True)
    game_world.add_object(stage_colliders, 1)



    #grass = Grass()
    #game_world.add_object(grass, 0)

    game_world.add_object(p1, 2)
    game_world.add_object(p2, 2)

    sword = Sword(2)
    game_world.add_object(sword, 2)

#플레이어가 검을 먹는 그걸 하려고.
    game_world.add_collision_pair('char:sword', p1, None)
    game_world.add_collision_pair('char:sword', p2, None)
    game_world.add_collision_pair('char:sword', None, sword)

    # 이게 그냥 움직일 때도 닿을 때가 있는데, 아무리 생각해도 그때마다 체크해서 공격상태인지 보는 것보다 그냥 공격 하는 순간에만 이 그룹에 넣었다 빼는게 더 낫지 않나?
    game_world.add_collision_pair('attack_sword:char', None, p1)
    game_world.add_collision_pair('attack_sword:char', None, p2)






def update():
    game_world.update()
    game_world.handle_collisions()



def draw():
    clear_canvas()
    game_world.render()
    update_canvas()

def finish():
    pass





