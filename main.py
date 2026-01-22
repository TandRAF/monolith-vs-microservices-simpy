import pygame
import random
from collections import deque

# --- CONFIGURATION ---
WIDTH, HEIGHT = 1200, 850
FPS = 60
MONO_LIMIT = 40
SVC_LIMIT = 25 
DB_CAPACITY = 35
HISTORY_LEN = 200

# Colors
BG = (10, 10, 15)
MONO_COLOR = (0, 180, 255)
AUTH_COLOR = (200, 0, 255)
ORDER_COLOR = (255, 140, 0)
DB_COLOR = (140, 140, 150)
ERROR_RED = (255, 50, 50)
SUCCESS_GREEN = (0, 255, 100)
DEAD_COLOR = (45, 45, 50)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
font = pygame.font.SysFont("Consolas", 14)
title_font = pygame.font.SysFont("Consolas", 22, bold=True)

class Request:
    def __init__(self, mode):
        self.pos = pygame.math.Vector2(30, random.randint(200, 600))
        self.mode = mode
        self.status = "to_auth" 
        self.target_idx = 0
        self.timer = 0
        self.color = (255, 255, 255)

class SystemManager:
    def __init__(self, mode):
        self.mode = mode
        self.requests = []
        self.success_history = deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN)
        self.fail_history = deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN)
        self.db_rect = pygame.Rect(1000, 350, 80, 120)
        self.db_queue = []
        
        if mode == "MONOLITH":
            self.main_block = pygame.Rect(450, 300, 200, 220)
            self.alive = [True] 
        else:
            self.auth_rect = pygame.Rect(320, 350, 100, 100)
            self.order_rects = [pygame.Rect(650, 250, 100, 100), 
                                pygame.Rect(650, 450, 100, 100)]
            self.alive = [True, True, True] 

    def update(self, flow_rate):
        if random.random() < flow_rate:
            self.requests.append(Request(self.mode))

        success_frame = 0
        fail_frame = 0

        # 1. CRASH LOGIC
        if self.mode == "MONOLITH" and self.alive[0]:
            load = len([r for r in self.requests if r.status in ["in_db", "to_db"]])
            if load >= MONO_LIMIT: self.alive[0] = False
        else:
            for i in [1, 2]:
                if len(self.alive) > i and self.alive[i]:
                    svc_load = len([r for r in self.requests if r.status == "to_db" and r.target_idx == i])
                    if svc_load >= SVC_LIMIT: self.alive[i] = False

        # 2. DB LOGIC
        db_full = len(self.db_queue) > DB_CAPACITY
        to_remove_db = []
        for r in self.db_queue:
            r.timer += 1
            limit = 70 if db_full else 25
            if r.timer > limit:
                if db_full and random.random() < 0.5: r.status = "failed"
                else: r.status = "done"; success_frame += 1
                to_remove_db.append(r)
        
        for r in to_remove_db:
            if r in self.db_queue: self.db_queue.remove(r)
            if r in self.requests: self.requests.remove(r)

        # 3. MOVEMENT & CHAIN
        for r in self.requests[:]:
            if r.status == "failed":
                fail_frame += 1
                r.color = ERROR_RED
                r.pos.x += 15
                if r.pos.x > WIDTH: self.requests.remove(r)
                continue

            if self.mode == "MONOLITH":
                if not self.alive[0]: r.status = "failed"
                elif r.status == "to_auth":
                    r.pos.move_towards_ip(self.main_block.center, 8)
                    if self.main_block.collidepoint(r.pos): r.status = "to_db"
                elif r.status == "to_db":
                    r.pos.move_towards_ip(self.db_rect.center, 12)
                    if self.db_rect.collidepoint(r.pos):
                        self.db_queue.append(r); r.status = "in_db"; r.timer = 0
            else:
                if r.status == "to_auth":
                    r.pos.move_towards_ip(self.auth_rect.center, 8)
                    if self.auth_rect.collidepoint(r.pos):
                        if not self.alive[0]: r.status = "failed"
                        else:
                            targets = [i for i in [1, 2] if self.alive[i]]
                            if not targets: r.status = "failed"
                            else:
                                r.target_idx = random.choice(targets)
                                r.status = "to_order"
                elif r.status == "to_order":
                    target_rect = self.order_rects[r.target_idx-1]
                    r.pos.move_towards_ip(target_rect.center, 9)
                    if target_rect.collidepoint(r.pos): r.status = "to_db"
                elif r.status == "to_db":
                    r.pos.move_towards_ip(self.db_rect.center, 12)
                    if self.db_rect.collidepoint(r.pos):
                        self.db_queue.append(r); r.status = "in_db"; r.timer = 0

        self.success_history.append(min(120, success_frame * 12))
        self.fail_history.append(min(120, fail_frame * 8))

    def draw(self):
        db_c = ERROR_RED if len(self.db_queue) > DB_CAPACITY else DB_COLOR
        pygame.draw.rect(screen, db_c, self.db_rect, 3)
        screen.blit(font.render("DATABASE", True, db_c), (1000, 330))

        if self.mode == "MONOLITH":
            c = MONO_COLOR if self.alive[0] else DEAD_COLOR
            pygame.draw.rect(screen, c, self.main_block, 4)
            screen.blit(font.render("MONOLITH", True, c), (450, 280))
            
            load = len([r for r in self.requests if r.status in ["to_db", "in_db"]])
            pct = min(1.0, load / MONO_LIMIT)
            pygame.draw.rect(screen, (50,50,50), (450, 530, 200, 10))
            pygame.draw.rect(screen, ERROR_RED if not self.alive[0] else MONO_COLOR, (450, 530, 200 * pct, 10))
            screen.blit(font.render(f"THREADS: {load}/{MONO_LIMIT}", True, c), (450, 545))
        else:
            # AUTH
            auth_c = AUTH_COLOR if self.alive[0] else DEAD_COLOR
            pygame.draw.rect(screen, auth_c, self.auth_rect, 2)
            screen.blit(font.render("AUTH", True, auth_c), (320, 330))
            
            # ORDERS
            for i in [1, 2]:
                order_c = ORDER_COLOR if self.alive[i] else DEAD_COLOR
                rect = self.order_rects[i-1]
                pygame.draw.rect(screen, order_c, rect, 2)
                
                load = len([r for r in self.requests if r.status == "to_db" and r.target_idx == i])
                pct = min(1.0, load / SVC_LIMIT)
                pygame.draw.rect(screen, (50,50,50), (rect.x, rect.y + 110, 100, 8))
                pygame.draw.rect(screen, ERROR_RED if not self.alive[i] else ORDER_COLOR, (rect.x, rect.y + 110, 100 * pct, 8))
                screen.blit(font.render(f"THREADS: {load}/{SVC_LIMIT}", True, order_c), (rect.x, rect.y + 120))    
                status = "ACTIVE" if self.alive[i] else "CRASHED"
                screen.blit(font.render(f"ORDER {i}: {status}", True, order_c), (rect.x, rect.y-20))

        for r in self.requests:
            if r.status != "done": pygame.draw.circle(screen, r.color, (int(r.pos.x), int(r.pos.y)), 4)

def draw_graphs(sys):
    pygame.draw.rect(screen, (20, 20, 30), (50, 680, 500, 140))
    screen.blit(font.render("SUCCESS RATE", True, SUCCESS_GREEN), (60, 690))
    for i in range(1, len(sys.success_history)):
        pygame.draw.line(screen, SUCCESS_GREEN, (50+i*2.5, 800 - sys.success_history[i]), (50+(i-1)*2.5, 800 - sys.success_history[i-1]), 2)
    
    pygame.draw.rect(screen, (20, 20, 30), (600, 680, 500, 140))
    screen.blit(font.render("FAILURE RATE", True, ERROR_RED), (610, 690))
    for i in range(1, len(sys.fail_history)):
        pygame.draw.line(screen, ERROR_RED, (600+i*2.5, 800 - sys.fail_history[i]), (600+(i-1)*2.5, 800 - sys.fail_history[i-1]), 2)

# --- EXECUTION ---
sys_mgr = SystemManager("MONOLITH")
flow = 0.1
clock = pygame.time.Clock()

while True:
    screen.fill(BG)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c: sys_mgr = SystemManager("MICRO") if sys_mgr.mode == "MONOLITH" else SystemManager("MONOLITH")
            if event.key == pygame.K_UP: flow = min(1.0, flow + 0.1)
            if event.key == pygame.K_DOWN: flow = max(0.0, flow - 0.1)
            if event.key == pygame.K_r: sys_mgr.alive = [True]*len(sys_mgr.alive); sys_mgr.requests = []; sys_mgr.db_queue = []
            
            if event.key == pygame.K_1: 
                sys_mgr.alive[0] = not sys_mgr.alive[0]
            if event.key == pygame.K_2: 
                if len(sys_mgr.alive) > 1: sys_mgr.alive[1] = not sys_mgr.alive[1]
            if event.key == pygame.K_3: 
                if len(sys_mgr.alive) > 2: sys_mgr.alive[2] = not sys_mgr.alive[2]

    sys_mgr.update(flow)
    sys_mgr.draw()
    draw_graphs(sys_mgr)
    
    screen.blit(title_font.render(f"ARCHITECTURE: {sys_mgr.mode} | FLOW: {int(flow*100)}%", True, (255, 255, 255)), (20, 20))
    screen.blit(font.render("[C]Swap [UP/DOWN]Flow [R]Reboot [1]Auth/Mono [2]Order1 [3]Order2", True, (150, 150, 150)), (20, 55))
    pygame.display.flip()
    clock.tick(FPS)