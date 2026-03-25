# patterns/tetris.py
import time
import random
from .base import Pattern as BasePattern, apply_modulation
from colormaps import COLORMAPS

# — Adjustable Parameters —
PARAMS = {
    "SPEED": {
        "default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1,
        "modulatable": True
    },
    "RANDOMNESS": {
        "default": 0.2, "min": 0.0, "max": 1.0, "step": 0.05,
        "modulatable": True
    },
    "COLOR_OFFSET": {
        "default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    "COLOR_SPREAD": {
        "default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01,
        "modulatable": True
    },
    # allow user to pick a colormap
    "COLORMAP": {
        "default": "jet",
        "options": list(COLORMAPS.keys())
    }
}

# Tetromino definitions: list of rotation states, each a list of (x,y)
TETROMINOES = {
    'I': [[(0,1),(1,1),(2,1),(3,1)], [(2,0),(2,1),(2,2),(2,3)]],
    'O': [[(1,0),(2,0),(1,1),(2,1)]],
    'T': [[(1,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(2,1),(1,2)],
          [(0,1),(1,1),(2,1),(1,2)], [(1,0),(0,1),(1,1),(1,2)]],
    'S': [[(1,0),(2,0),(0,1),(1,1)], [(1,0),(1,1),(2,1),(2,2)]],
    'Z': [[(0,0),(1,0),(1,1),(2,1)], [(2,0),(1,1),(2,1),(1,2)]],
    'J': [[(0,0),(0,1),(1,1),(2,1)], [(1,0),(2,0),(1,1),(1,2)],
          [(0,1),(1,1),(2,1),(2,2)], [(1,0),(1,1),(0,2),(1,2)]],
    'L': [[(2,0),(0,1),(1,1),(2,1)], [(1,0),(1,1),(1,2),(2,2)],
          [(0,1),(1,1),(2,1),(0,2)], [(0,0),(1,0),(1,1),(1,2)]]
}

class Pattern(BasePattern):
    def __init__(self, width, height, params=None):
        super().__init__(width, height, params)
        self.param_meta = PARAMS
        self.reset()

    def reset(self):
        """(Re)initialize game state"""
        self.board = [[ None for _ in range(self.width) ]
                       for __ in range(self.height)]
        self.next_piece = self.random_piece()
        self.spawn_new_piece()
        self.last_time = time.time()
        self.drop_accum = 0.0

    def random_piece(self):
        """Pick a random tetromino and rotation state"""
        kind = random.choice(list(TETROMINOES.keys()))
        rots = TETROMINOES[kind]
        r = random.randrange(len(rots))
        return dict(kind=kind, rot=r, shape=rots[r])

    def spawn_new_piece(self):
        """Move next_piece into current, pick a fresh next"""
        self.cur = self.next_piece
        self.next_piece = self.random_piece()
        # start at top center
        self.cur_x = (self.width // 2) - 2
        self.cur_y = 0

    def can_place(self, shape, x, y):
        for dx,dy in shape:
            bx, by = x+dx, y+dy
            if bx<0 or bx>=self.width or by<0 or by>=self.height:
                return False
            if self.board[by][bx] is not None:
                return False
        return True

    def lock_piece(self):
        for dx,dy in self.cur['shape']:
            bx, by = self.cur_x+dx, self.cur_y+dy
            if 0 <= by < self.height:
                self.board[by][bx] = self.cur['kind']
        # clear any full lines
        newb = [row for row in self.board if any(cell is None for cell in row)]
        lines_cleared = self.height - len(newb)
        for _ in range(lines_cleared):
            newb.insert(0, [None]*self.width)
        self.board = newb
        self.spawn_new_piece()

    def step(self, dt, speed, randomness):
        """Advance the game by dt seconds"""
        self.drop_accum += dt * speed
        while self.drop_accum >= 1.0:
            self.drop_accum -= 1.0
            # attempt to move piece down
            if self.can_place(self.cur['shape'], self.cur_x, self.cur_y+1):
                self.cur_y += 1
            else:
                # lock and choose next
                self.lock_piece()
                return
        # if piece has just spawned, let AI choose a column & rotation
        if self.cur_y == 0 and randomness is not None:
            if random.random() < randomness:
                # random placement
                rots = TETROMINOES[self.cur['kind']]
                self.cur['rot'] = random.randrange(len(rots))
                self.cur['shape'] = rots[self.cur['rot']]
                self.cur_x = random.randrange(self.width - 3)
            else:
                # greedy: try all rotations & columns, pick one with lowest landing height
                best = None
                for r,shape in enumerate(TETROMINOES[self.cur['kind']]):
                    for x in range(self.width-3):
                        y=0
                        while self.can_place(shape, x, y+1):
                            y+=1
                        # compute highest filled row after drop
                        worst = max((y+dy) for _,dy in shape)
                        score = worst
                        if best is None or score < best[0]:
                            best = (score, x, r)
                if best:
                    _, bx, br = best
                    self.cur_x = bx
                    self.cur['rot'] = br
                    self.cur['shape'] = TETROMINOES[self.cur['kind']][br]

    def render(self, lfo_signals=None):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        # 1) Read & modulate parameters
        speed  = self.params["SPEED"]
        randm  = self.params["RANDOMNESS"]
        coff   = self.params["COLOR_OFFSET"]
        spread = self.params["COLOR_SPREAD"]
        for key in ("SPEED","RANDOMNESS","COLOR_OFFSET","COLOR_SPREAD"):
            meta = self.param_meta[key]
            if meta.get("modulatable") and meta.get("mod_active"):
                src = meta.get("mod_source")
                amt = (lfo_signals or {}).get(src, 0.0)
                val = apply_modulation(self.params[key], meta, amt)
                if   key=="SPEED":        speed  = val
                elif key=="RANDOMNESS":   randm  = val
                elif key=="COLOR_OFFSET": coff   = val
                elif key=="COLOR_SPREAD": spread = val

        # 2) Advance game state
        self.step(dt, speed, randm)

        # 3) Pick colormap
        cmap = COLORMAPS[self.params.get("COLORMAP","jet")]
        N    = len(cmap)

        # 4) Build pixel frame
        frame = []
        # first draw locked blocks
        for y in range(self.height):
            for x in range(self.width):
                cell = self.board[y][x]
                if cell is None:
                    frame.append((0,0,0,0))
                else:
                    # map piece character → color index
                    idx0 = (ord(cell) - ord('A')) / 7.0
                    frac = (coff + idx0 * spread) % 1.0
                    col = cmap[int(frac*(N-1))]
                    frame.append((*col,0))
        # then overlay current piece
        for dx,dy in self.cur['shape']:
            px,py = self.cur_x+dx, self.cur_y+dy
            if 0 <= px < self.width and 0 <= py < self.height:
                idx = py*self.width + px
                frac = (coff + 6/7*spread) % 1.0
                col = cmap[int(frac*(N-1))]
                frame[idx] = (*col,0)

        return frame
