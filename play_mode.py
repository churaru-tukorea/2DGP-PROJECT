from pico2d import *
from character import Character
import game_world
from grass import Grass
from sword import Sword
import random

from static_image_layer import StaticImageLayer
from stage_colliders import StageColliders
from items import SpeedClockItem, AttackClockItem
import game_framework
import config
from spear import Spear
from ai_controller import CharacterAI
import scramble_nav


running = True
character = None
stage_colliders = None

item_spawn_time = None   # 아이템이 처음 나올 시간
item_spawned = False     # 이미 한 번이라도 스폰됐는지 여부
item_spawn_interval = None

p1 = None
p2 = None
sword = None
cpu_ai = None   # ← AI 컨트롤러 전역


def handle_events():
    global running

    event_list = get_events()
    for event in event_list:
        if event.type == SDL_QUIT:
            running = False

        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
            exit()

        # 플레이 중에도 i를 누르면 무기 선택 모드로 넘어감
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            import item_mode
            game_framework.change_mode(item_mode)

        else:
            p1.handle_event(event)
            if cpu_ai is None:
                p2.handle_event(event)





def init():
    global p1, p2, running, sword, stage_colliders
    global item_spawn_time, item_spawned, item_spawn_interval
    global cpu_ai

    running = True
    item_spawned = False

    # 플레이어 생성
    p1 = Character(pid=1)
    p1.x = 300
    p2 = Character(pid=2)
    p2.x = 900

    # p2를 AI로 조종
    cpu_ai = CharacterAI(p2, p1)

    # 배경
    background_layer = StaticImageLayer('background.png', fit='cover')
    game_world.add_object(background_layer, 0)

    boss_stage_layer = StaticImageLayer('boss stage.png', fit='cover')
    game_world.add_object(boss_stage_layer, 1)

    stage_colliders = StageColliders(boss_stage_layer, debug=True)
    game_world.add_object(stage_colliders, 1)

    # 캐릭터
    game_world.add_object(p1, 2)
    game_world.add_object(p2, 2)

    game_world.add_collision_pair('char:stage', p1, stage_colliders)
    game_world.add_collision_pair('char:stage', p2, stage_colliders)

    p1.use_stage_collision = True
    p2.use_stage_collision = True

    # --- 무기 모드에 따라 무기 셋업 ---
    weapon_mode = getattr(config, 'weapon_mode', 'sword')
    print(f'[play_mode] weapon_mode = {weapon_mode}')

    if weapon_mode == 'sword':
        sword = Sword(2)
        sword.bind_stage(stage_colliders) # 스테이지 연동 여기서 해버리기
        game_world.add_object(sword, 2)

        # AI에 nav 컨텍스트 연결
        cpu_ai.set_scramble_context(stage_colliders, lambda: sword)

        # 플레이어가 검을 줍는 충돌 그룹
        game_world.add_collision_pair('char:sword', p1, None)
        game_world.add_collision_pair('char:sword', p2, None)
        game_world.add_collision_pair('char:sword', None, sword)

        # 공격 중 칼 vs 캐릭터
        game_world.add_collision_pair('attack_sword:char', None, p1)
        game_world.add_collision_pair('attack_sword:char', None, p2)

    elif weapon_mode == 'spear':
        # 아직 spear는 구현 전이라 이렇게.
        print('[play_mode] spear 모드는 아직 구현 전입니다. 일단 sword 모드로 동작합니다.')
        spear = Spear(2)
        spear.bind_stage(stage_colliders)
        game_world.add_object(spear, 2)

        cpu_ai.set_scramble_context(stage_colliders, lambda: spear)

        game_world.add_collision_pair('char:spear', p1, None)
        game_world.add_collision_pair('char:spear', p2, None)
        game_world.add_collision_pair('char:spear', None, spear)

        game_world.add_collision_pair('char:spear', None, spear)
        game_world.add_collision_pair('attack_spear:char', spear, p1)
        game_world.add_collision_pair('attack_spear:char', None, p2)

        #game_world.add_collision_pair('attack_spear:stage', spear, stage_colliders)

    # 아이템(시계) 충돌 그룹 – 플레이어 쪽 먼저
    game_world.add_collision_pair('char:item', p1, None)
    game_world.add_collision_pair('char:item', p2, None)

    # 아이템 스폰 타이머
    item_spawn_interval = 10.0
    item_spawn_time = get_time() + item_spawn_interval






def update():
    global item_spawn_time, item_spawned, stage_colliders, item_spawn_interval

    now = get_time()

    if cpu_ai is not None:
        cpu_ai.update()

    # 아이템 스폰: 게임 시작 후 10초에 한 번, 아직 안 나왔을 때만
    if (not item_spawned) and item_spawn_time is not None and now >= item_spawn_time:
        cw = get_canvas_width()
        query_bb = (0, -1000, cw, 1000)
        near = stage_colliders.query_boxes(query_bb, margin=0.0)

        # 1) nav에서 무시하는 플랫폼(ceiling, left_wall, right_wall)은 스폰 후보에서 제외
        candidates = [
            info for info in near
            if info[0] not in scramble_nav.IGNORED_PLATFORMS
        ]

        if candidates:
            # (name, typ, L, B, R, T) 구조
            name, typ, L, B, R, T = random.choice(candidates)

            item_w = 48
            item_h = 48
            margin_x = item_w * 0.5 + 4  # 양 끝 여유

            if R - L <= margin_x * 2:
                spawn_x = (L + R) * 0.5
            else:
                spawn_x = random.uniform(L + margin_x, R - margin_x)

            # 아이템이 플랫폼 바로 위에 보이도록 (센터 = T + 반높이 정도)
            spawn_y = T + item_h * 0.5

            if random.random() < 0.5:
                item = SpeedClockItem(spawn_x, spawn_y)
            else:
                item = AttackClockItem(spawn_x, spawn_y)

            game_world.add_object(item, 2)
            game_world.add_collision_pair('char:item', None, item)

        # 후보가 없든 있든, 다음 스폰 타이밍은 갱신
        item_spawn_time = now + item_spawn_interval


           #item_spawned = True


    game_world.update()
    game_world.handle_collisions()



def draw():
    clear_canvas()
    game_world.render()

    # 추가된 부분: AI가 뭘 생각하는지 그리기
    if cpu_ai:
        cpu_ai.draw()


    update_canvas()

def finish():
    # 월드와 충돌 페어를 전부 정리하고, 레퍼런스도 끊는다
    game_world.clear()
    game_world.collision_pairs.clear()  # ← 충돌 그룹까지 초기화
    global p1, p2, stage_colliders, sword
    try:
        # spear 전역도 같이 정리(있다면)
        global spear
    except NameError:
        pass
    p1 = p2 = stage_colliders = sword = None
    try:
        spear = None
    except:
        pass





