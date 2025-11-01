#world[0]: 0번 레이어
#world[1]: 1번 레이어
#world[2]: 2번 레이어


world = [[], [], []] # 게임 내 객체들을 담는 리스트

def add_object(o, depth = 0): # 게임 월드의 객체를 추가하는 함수
    world[depth].append(o)

#게임 월드에 객체 리스트를 추가하는 함수
def add_objects(ol, depth = 0): #add_objects([ball1, ball2]) 이게 가능해 지는거임. 리스트 안에 있는 객체를 통채로 다 더해준다.
    world[depth] += ol


def update(): # 게임 월드의 모든 객체를 업데이트하는 함수
    for layer in world:
        for o in layer:
            o.update()


def render(): # 게임 월드의 모든 객체를 그리는 함수
    for layer in world:
        for o in layer:
            o.draw()


def remove_object(o): # 게임 월드의 객체를 제거하는 함수
    #하다 보면 프로그램 오류로 인해서 게임 월드에 들어있지도 않은 객체를 지우려고 할떄가 있다. 그래서 체크를 해야 한다.
    for layer in world:
        if o in layer:
            layer.remove(o)
            return #return 하는 이유는 찾아지지 않았을 경우 에러를 출력하기 위해
    raise Exception('월드에 존재하지 않은 객체를 삭제하려고 합니다.')
    #이렇게 하는게 안전하다.

def clear():
    for layer in world:
        layer.clear()
