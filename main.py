from pico2d import *
from character import Character





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





def reset_world():

    global world
    global character


    world = []


    character = Character()
    world.append(character)





def update_world():
    for o in world:
        o.update()
    pass



def render_world():
    clear_canvas()
    for o in world:
        o.draw()
    pass



running = True



open_canvas()
reset_world()

while running:
    handle_events()
    update_world()
    render_world()
    delay(0.01)

close_canvas()