from pico2d import *
from character import Character
import game_world
from grass import Grass
from sword import Sword
import random

from static_image_layer import StaticImageLayer
from stage_colliders import StageColliders
from items import SpeedClockItem, AttackClockItem


running = True
character = None
stage_colliders = None

item_spawn_time = None   # 아이템이 처음 나올 시간
item_spawned = False     # 이미 한 번이라도 스폰됐는지 여부


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
    global stage_colliders
    global item_spawn_time, item_spawned


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

    game_world.add_collision_pair('char:stage', p1, stage_colliders)
    game_world.add_collision_pair('char:stage', p2, stage_colliders)

    p1.use_stage_collision = True
    p2.use_stage_collision = True

    sword = Sword(2)
    game_world.add_object(sword, 2)

#플레이어가 검을 먹는 그걸 하려고.
    game_world.add_collision_pair('char:sword', p1, None)
    game_world.add_collision_pair('char:sword', p2, None)
    game_world.add_collision_pair('char:sword', None, sword)

    # 아이템(시계)용 충돌 그룹 – 플레이어 쪽만 먼저 등록
    game_world.add_collision_pair('char:item', p1, None)
    game_world.add_collision_pair('char:item', p2, None)


    # 이게 그냥 움직일 때도 닿을 때가 있는데, 아무리 생각해도 그때마다 체크해서 공격상태인지 보는 것보다 그냥 공격 하는 순간에만 이 그룹에 넣었다 빼는게 더 낫지 않나?
    game_world.add_collision_pair('attack_sword:char', None, p1)
    game_world.add_collision_pair('attack_sword:char', None, p2)

    # 아이템 스폰 타이머: 게임 시작 후 10초 뒤 한 번
    item_spawn_time = get_time() + 10.0
    item_spawned = False






def update():
    global item_spawn_time, item_spawned, stage_colliders

    now = get_time()

    # 아이템 스폰: 게임 시작 후 10초에 한 번, 아직 안 나왔을 때만
    if (not item_spawned) and item_spawn_time is not None and now >= item_spawn_time:
        cw = get_canvas_width()
        # 화면 전체를 커버하는 큰 AABB로 질의
        query_bb = (0, -1000, cw, 1000)
        near = stage_colliders.query_boxes(query_bb, margin=0.0)

        if near:
            # (_, typ, L, B, R, T) 형태라고 가정 (char의 _solve_stage_collision과 동일)
            _, typ, L, B, R, T = random.choice(near)

            item_w = 48
            item_h = 48
            margin_x = item_w * 0.5 + 4  # 양 끝살짝 여유를 둠

            if R - L <= margin_x * 2:
                spawn_x = (L + R) * 0.5
            else:
                spawn_x = random.uniform(L + margin_x, R - margin_x)

            # 아이템이 바닥에 딱 붙도록(센터 = 플랫폼 위 + 반높이)
            spawn_y = T + item_h * 0.5

            # 두 종류 중 하나를 랜덤 선택
            if random.random() < 0.5:
                item = SpeedClockItem(spawn_x, spawn_y)
            else:
                item = AttackClockItem(spawn_x, spawn_y)

            game_world.add_object(item, 2)
            # char:item 그룹의 반대편(아이템 쪽)에 등록
            game_world.add_collision_pair('char:item', None, item)

            item_spawned = True

    game_world.update()
    game_world.handle_collisions()



def draw():
    clear_canvas()
    game_world.render()
    update_canvas()

def finish():
    pass





