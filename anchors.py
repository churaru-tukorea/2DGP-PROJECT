import csv

# 필요한 액션만: idle(2프), move(10프), attack_fire(7프)
ANCHOR = { 'idle': {}, 'move': {}, 'attack_fire': {} }

def load_csv(path='anchor_from_sword_sheet.csv'):
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            act = row['action'].strip()
            if act not in ANCHOR:  # 정의 안 한 액션은 무시
                continue
            fi  = int(row['frame'])
            u   = float(row['hand_x_norm'])
            v   = float(row['hand_y_norm'])
            deg = float(row['sword_deg'])
            ANCHOR[act][fi] = (u, v, deg)