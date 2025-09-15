from pico2d import *

import math

open_canvas()

character = load_image('character.png')
grass = load_image('grass.png')


def draw_rectangle():
    x = 400
    y = 90
    while(x<780):
        clear_canvas_now()
        grass.draw_now(400,30)
        character.draw_now(x,y)
        x = x + 2
        delay(0.01)
    while(y<570):
        clear_canvas_now()
        grass.draw_now(400,30)
        character.draw_now(x,y)
        y = y + 2
        delay(0.01)
    while(x>10):
        clear_canvas_now()
        grass.draw_now(400,30)
        character.draw_now(x,y)
        x = x - 2
        delay(0.01)
    while(y>92):
        clear_canvas_now()
        grass.draw_now(400,30)
        character.draw_now(x,y)
        y = y - 2
        delay(0.01)
    while(x<400):
        clear_canvas_now()
        grass.draw_now(400,30)
        character.draw_now(x,y)
        x = x + 2
        delay(0.01)

def draw_circle():
    x = 400
    y = 300
    r = 210
    angle = -90
    while(angle<270):
        clear_canvas_now()
        grass.draw_now(400,30)
        cx = x + r * math.cos(math.radians(angle))
        cy = y + r * math.sin(math.radians(angle))
        character.draw_now(cx,cy)
        angle = angle + 2
        delay(0.01)




while True:
    draw_rectangle()
    draw_circle()





close_canvas()
