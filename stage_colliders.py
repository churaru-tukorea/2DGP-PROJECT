from pico2d import draw_rectangle
import stage_layout  # STAGE_SOURCE_SIZE, STAGE_BOXES 사용

class StageColliders:

    def __init__(self, boss_stage_layer, debug=True):
        self.boss_stage_layer = boss_stage_layer
        self.debug = debug
        self._cache_key = None
        self.screen_boxes = []  # [(name, type, Lp,Bp,Rp,Tp), ...]
        self.rebuild()

    def _layout_key(self):
        s, dx, dy, _, _ = self.boss_stage_layer.get_fit_params()
        # 너무 자주 재빌드되지 않게 적당히 라운딩
        return (round(s, 6), round(dx, 2), round(dy, 2))

    def rebuild(self):
        s, dx, dy, iw, ih = self.boss_stage_layer.get_fit_params()
        SW, SH = stage_layout.STAGE_SOURCE_SIZE

        dw = s * iw
        dh = s * ih

        sx = dw / SW
        sy = dh / SH

        boxes = []
        for name, typ, L, B, R, T in stage_layout.STAGE_BOXES:
            if L > R: L, R = R, L
            if B > T: B, T = T, B
            Lp = dx + L * sx
            Rp = dx + R * sx
            Bp = dy + B * sy
            Tp = dy + T * sy
            boxes.append((name, typ, Lp, Bp, Rp, Tp))
        self.screen_boxes = boxes
        self._cache_key = self._layout_key()

    def update(self):
        # boss_stage 레이아웃이 변하면 자동 재계산
        if self._layout_key() != self._cache_key:
            self.rebuild()

    def draw(self):
        if not self.debug:
            return
        # 디버그: 스크린 AABB 외곽선을 그려 정렬 확인
        for _, _, Lp, Bp, Rp, Tp in self.screen_boxes:
            draw_rectangle(Lp, Bp, Rp, Tp)

    # 충돌 단계에서 쓸 수 있도록 getter도 준비
    def get_screen_boxes(self):
        return self.screen_boxes