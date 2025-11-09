#world[0]: 0번 레이어
#world[1]: 1번 레이어
#world[2]: 2번 레이어


world = [[], [], [],[]] # 게임 내 객체들을 담는 리스트

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


def remove_collision_object(o):
  for pairs in collision_pairs.values():
   if o in pairs[0]:
     pairs[0].remove(o)
   if o in pairs[1]:
     pairs[1].remove(o)

def remove_object(o):
    for layer in world:
        if o in layer:
            layer.remove(o)
            remove_collision_object(o)
            return

    raise ValueError('Cannot delete non existing object')


def clear():
    global world

    for layer in world:
        layer.clear()


def collide(a, b):
    # --- 기존과 완전히 동일한 AABB 경로 ---
    if not hasattr(a, 'get_obb') and not hasattr(b, 'get_obb'):
        l1,b1,r1,t1 = a.get_bb(); l2,b2,r2,t2 = b.get_bb()
        return not (l1 > r2 or r1 < l2 or t1 < b2 or b1 > t2)

    # --- 여기서부터만 OBB 필요할 때 사용 ---
    def corners(o):
        if hasattr(o, 'get_obb'):
            return o.get_obb()
        l,b,r,t = o.get_bb()
        return ((l,b),(r,b),(r,t),(l,t))

    A, B = corners(a), corners(b)

    def axes(poly):
        x0,y0=poly[0]; x1,y1=poly[1]; x2,y2=poly[2]
        return [ (-(y1-y0), x1-x0), (-(y2-y1), x2-x1) ]  # 두 법선이면 충분

    def proj(poly, ax, ay):
        vals = [x*ax + y*ay for x,y in poly]
        return min(vals), max(vals)

    for ax, ay in axes(A) + axes(B):
        a0,a1 = proj(A,ax,ay); b0,b1 = proj(B,ax,ay)
        if a1 < b0 or b1 < a0:
            return False
    return True

collision_pairs = {}
#boy:ball 이라는게 그룹 이름이 되고, 그 안에 키와 value로 들어가나?
def add_collision_pair(group, a, b):
    if group not in collision_pairs:#처음 추가되는 그룹이면
        print(f'Added new group {group}')
        collision_pairs[group] = [[], []]#해당 그룹에 대해서 초기화
    if a:
            collision_pairs[group][0].append(a)
    if b:
            collision_pairs[group][1].append(b)


def handle_collisions():
    for group, pairs in collision_pairs.items():
        for a in pairs[0]:
            for b in pairs[1]:
                if collide(a, b):
                    print(f'COLLIDE[{group}] {a} <-> {b}')
                    a.handle_collision(group, b)
                    b.handle_collision(group, a)

#내가 보낸 그룹 안에 있는 그걸 지워버리는
def remove_collision_object_once(self, group):
    if group in collision_pairs:
        pairs = collision_pairs[group]
        if self in pairs[0]:
            pairs[0].remove(self)
            return True
        if self in pairs[1]:
            pairs[1].remove(self)
            return True
    return None