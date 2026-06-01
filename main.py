import pygame
import sys
import math
import random
from sprites import Player, Tile, Enemy, FuelCell, Checkpoint, SpaceshipRed

# Dimensões da tela do jogo
WIDTH = 800
HEIGHT = 520
FPS = 60

# Cores do sistema
COLOR_BG = (2, 6, 23)
COLOR_NEON_BLUE = (14, 165, 233)
COLOR_ACCENT = (245, 158, 11)
COLOR_NEON_GREEN = (16, 185, 129)
COLOR_NEON_RED = (239, 68, 68)

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Tela e título
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Cadu's Cosmic Quest: The Adventures of GIF")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Configurações com persistência simulada (ou padrão)
        self.volume_music = 0.3
        self.volume_sfx = 0.5
        self.difficulty = 'normal'
        self.show_touch_controls = False
        self.is_muted = False
        self.fullscreen = False
        
        # Gerenciamento de Cenas: 'menu', 'hub', 'play'
        self.current_scene = 'menu'
        self.current_planet = 'hub'
        self.unlocked_planets = ['hub', 'cristal']
        self.collected_fuel = 0
        self.active_checkpoint = (100, 350, "Hangar Alfa")
        
        # Câmera (x offset)
        self.camera_x = 0
        self.camera_shake_timer = 0
        self.camera_shake_intensity = 0
        
        # Inicializar fontes
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial Black", 20)
        self.font_body = pygame.font.SysFont("Arial", 14)
        self.font_hud = pygame.font.SysFont("Arial Black", 13)
        self.font_btn = pygame.font.SysFont("Arial Black", 12)
        
        # Partículas
        self.particles = []
        
        # Sintetizar efeitos de som Chiptune na memória
        self.sounds = {}
        self.synthesize_chiptunes()
        
        # Carregamento de Recursos (Imagens com fallback)
        self.load_resources()
        
        # Loop de música tema
        self.music_notes = [
            [220, 261, 293, 329], # La, Do, Re, Mi
            [261, 329, 392, 440], # Do, Mi, Sol, La
            [293, 349, 440, 523]  # Re, Fa, La, Do
        ]
        self.melody_idx = 0
        self.note_idx = 0
        self.music_timer = 0
        
        # Inicializar entidades
        self.init_hub()
        self.init_play()
        
        # Estados de Modais
        self.modal_active = None # 'config', 'controls', 'briefing'
        self.briefing_data = {"title": "", "desc": "", "img": None}
        
        # Botões de toque clicáveis (simulando toque móvel por clique do mouse)
        self.touch_buttons = {
            "left": pygame.Rect(25, 435, 54, 54),
            "right": pygame.Rect(95, 435, 54, 54),
            "jump": pygame.Rect(650, 435, 54, 54),
            "jetpack": pygame.Rect(580, 435, 54, 54),
            "attack": pygame.Rect(720, 435, 54, 54)
        }
        self.touch_state = {"left": False, "right": False, "jump": False, "jetpack": False}

    def load_resources(self):
        # Pasta assets/
        p = "assets/"
        self.fallback_cover = False
        self.fallback_bg = False
        
        # Imagem de Capa
        try:
            self.cover_img = pygame.image.load(p + "cover.jpg").convert()
            # Redimensionar mantendo proporção para caber em 520px de altura
            h = HEIGHT
            w = int(self.cover_img.get_width() * (h / self.cover_img.get_height()))
            self.cover_img = pygame.transform.scale(self.cover_img, (w, h))
        except Exception as e:
            print(f"Erro ao carregar capa cover.jpg: {e}")
            self.fallback_cover = True
            
        # Fundos de planetas
        self.bg_textures = {}
        bg_files = {
            "hub": "background_pixar.jpg",
            "cristal": "background_cristal.jpg",
            "inferno": "background_inferno.jpg",
            "verdantis": "background_verdantis.jpg",
            "umbra": "background_umbra.jpg"
        }
        for k, name in bg_files.items():
            try:
                img = pygame.image.load(p + name).convert()
                self.bg_textures[k] = pygame.transform.scale(img, (WIDTH, HEIGHT))
            except Exception as e:
                print(f"Erro ao carregar fundo {name}: {e}")
                self.fallback_bg = True
                
        # Player face (HUD)
        try:
            self.player_face = pygame.image.load(p + "player_face.png").convert_alpha()
            self.player_face = pygame.transform.scale(self.player_face, (38, 38))
        except Exception as e:
            print(f"Erro ao carregar player_face.png: {e}")
            self.player_face = None

    def synthesize_chiptunes(self):
        # Gera sons de 8 bits diretamente convertendo ondas matemáticas para buffers PCM de 16 bits mono
        sample_rate = 44100
        
        def make_sine_sound(freq_func, duration, volume=0.08):
            num_samples = int(sample_rate * duration)
            buffer = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                freq = freq_func(t)
                val = int(32767 * volume * math.sin(2 * math.pi * freq * t))
                buffer.extend(val.to_bytes(2, byteorder='little', signed=True))
            return pygame.mixer.Sound(buffer=bytes(buffer))
            
        # Pulo: frequência exponencial de subida
        self.sounds['jump'] = make_sine_sound(lambda t: 140 + (580 - 140) * (t / 0.12)**2, 0.12, 0.12)
        # Dash: frequência de subida rápida
        self.sounds['dash'] = make_sine_sound(lambda t: 400 + 800 * (t / 0.1), 0.1, 0.12)
        # Ataque: frequência de queda rápida
        self.sounds['attack'] = make_sine_sound(lambda t: 350 - 200 * (t / 0.15), 0.15, 0.1)
        # Dano (hurt): queda grave
        self.sounds['hurt'] = make_sine_sound(lambda t: 180 - 135 * (t / 0.22), 0.22, 0.18)
        
        # Coleta: arpejo de 3 notas
        c5, e5, g5 = 523.25, 659.25, 783.99
        self.sounds['collect'] = make_sine_sound(
            lambda t: c5 if t < 0.08 else (e5 if t < 0.16 else g5), 0.24, 0.08
        )
        
        # Checkpoint: notas em sequência rápida
        self.sounds['checkpoint'] = make_sine_sound(
            lambda t: 440 if t < 0.1 else (554 if t < 0.2 else 659), 0.3, 0.08
        )

    def play_sound(self, name):
        if self.is_muted or name not in self.sounds:
            return
        self.sounds[name].play()

    def run_retro_music(self):
        # Toca a melodia tema MSX sem travar o loop principal (a cada 380ms)
        if self.is_muted:
            return
            
        self.music_timer += 1
        if self.music_timer >= 22: # Aproximadamente 360ms a 60 FPS
            self.music_timer = 0
            
            melody = self.music_notes[self.melody_idx]
            freq = melody[self.note_idx]
            
            # Tocar nota simples e curta sintetizada
            note_sound = self.synthesize_note(freq, 0.24, self.volume_music * 0.05)
            note_sound.play()
            
            self.note_idx = (self.note_idx + 1) % len(melody)
            if self.note_idx == 0:
                self.melody_idx = (self.melody_idx + 1) % len(self.music_notes)

    def synthesize_note(self, freq, duration, volume):
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        buffer = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            # Onda triangular leve
            val = int(32767 * volume * (2.0 * abs(2.0 * (t * freq - math.floor(t * freq + 0.5))) - 1.0))
            buffer.extend(val.to_bytes(2, byteorder='little', signed=True))
        return pygame.mixer.Sound(buffer=bytes(buffer))

    def init_hub(self):
        self.hub_platforms = pygame.sprite.Group()
        self.hub_terminal = pygame.sprite.Sprite()
        self.hub_spaceship = pygame.sprite.Sprite()
        
        # Chão
        for x in range(0, WIDTH, 40):
            tile = Tile(x, 480, 'solid', "assets/tile_solid.png")
            self.hub_platforms.add(tile)
            
        # Plataformas flutuantes
        for x in [150, 190, 230]:
            self.hub_platforms.add(Tile(x, 320, 'solid', "assets/tile_solid.png"))
        for x in [550, 590, 630]:
            self.hub_platforms.add(Tile(x, 260, 'solid', "assets/tile_solid.png"))
            
        # Nave vermelha e terminal
        self.hub_spaceship.image = pygame.Surface((100, 100), pygame.SRCALPHA)
        try:
            img = pygame.image.load("assets/spaceship_red.png").convert_alpha()
            self.hub_spaceship.image = pygame.transform.scale(img, (100, 100))
        except:
            pygame.draw.rect(self.hub_spaceship.image, COLOR_NEON_RED, (0,0,100,100), 2)
        self.hub_spaceship.rect = pygame.Rect(100, 380, 100, 100)
        
        self.hub_terminal.image = pygame.Surface((40, 80), pygame.SRCALPHA)
        try:
            img = pygame.image.load("assets/checkpoint_beacon.png").convert_alpha()
            self.hub_terminal.image = pygame.transform.scale(img, (40, 80))
        except:
            pygame.draw.rect(self.hub_terminal.image, COLOR_NEON_BLUE, (0,0,40,80))
        self.hub_terminal.rect = pygame.Rect(400, 400, 40, 80)
        
        # Player in Hub
        self.player_hub = Player(120, 350, "assets/astronaut_spritesheet.png")

    def init_play(self):
        self.play_platforms = pygame.sprite.Group()
        self.solid_blocks = pygame.sprite.Group()
        self.mystery_blocks = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.fuels = pygame.sprite.Group()
        
        # Chão da fase Cristal Prime (com buracos)
        for x in range(0, 2400, 40):
            # Abismos específicos
            if (320 < x < 440) or (840 < x < 980) or (1500 < x < 1680):
                continue
            tile = Tile(x, 480, 'ground', "assets/tile_ground.png")
            self.play_platforms.add(tile)
            
        # Plataformas flutuantes e blocos
        float_positions = [
            (250, 340, 'ground', "assets/tile_ground.png"),
            (290, 340, 'ground', "assets/tile_ground.png"),
            (450, 240, 'mystery', "assets/tile_mystery.png"),
            (490, 240, 'mystery', "assets/tile_mystery.png"),
            (530, 240, 'mystery', "assets/tile_mystery.png"),
            (700, 300, 'solid', "assets/tile_solid.png"),
            (740, 300, 'solid', "assets/tile_solid.png"),
            (780, 300, 'solid', "assets/tile_solid.png"),
            (1100, 350, 'ground', "assets/tile_ground.png"),
            (1140, 350, 'ground', "assets/tile_ground.png"),
            (1300, 230, 'mystery', "assets/tile_mystery.png"),
            (1340, 230, 'mystery', "assets/tile_mystery.png"),
            (1800, 320, 'solid', "assets/tile_solid.png"),
            (1840, 320, 'solid', "assets/tile_solid.png"),
            (1880, 320, 'solid', "assets/tile_solid.png")
        ]
        for x, y, t, img in float_positions:
            tile = Tile(x, y, t, img)
            if t == 'ground':
                self.play_platforms.add(tile)
            elif t == 'solid':
                self.solid_blocks.add(tile)
            elif t == 'mystery':
                self.mystery_blocks.add(tile)
                
        # 9 naves amarelas flutuantes
        fuel_positions = [
            (300, 400), (500, 180), (720, 220), (920, 320), (1200, 400),
            (1350, 150), (1550, 280), (1750, 200), (1950, 400)
        ]
        for x, y in fuel_positions:
            fuel = FuelCell(x, y, "assets/spaceship_yellow.png")
            self.fuels.add(fuel)
            
        # Inimigos
        slime1 = Enemy(600, 448, 'slime', "assets/enemy_slime.png")
        slime2 = Enemy(1200, 448, 'slime', "assets/enemy_slime.png")
        drone = Enemy(1600, 220, 'drone', "assets/enemy_drone.png")
        self.enemies.add(slime1, slime2, drone)
        
        # Checkpoint
        self.play_checkpoint = Checkpoint(950, 400, "assets/checkpoint_beacon.png")
        
        # Nave vermelha final
        self.play_spaceship = SpaceshipRed(2100, 360, "assets/spaceship_red.png")
        
        # Player
        self.player_play = Player(100, 350, "assets/astronaut_spritesheet.png")

    def create_particles(self, x, y, color, count):
        for _ in range(count):
            p = {
                "x": x,
                "y": y,
                "vx": (random.random() - 0.5) * 6,
                "vy": (random.random() - 0.5) * 6 - 3,
                "color": color,
                "alpha": 255,
                "life": random.randint(20, 40)
            }
            self.particles.append(p)

    def shake_camera(self, intensity):
        self.camera_shake_timer = 10
        self.camera_shake_intensity = intensity

    def respawn_player(self):
        self.player_play.health = 100
        self.player_play.hitbox.x = self.active_checkpoint[0]
        self.player_play.hitbox.y = self.active_checkpoint[1]
        self.player_play.vel_x = 0
        self.player_play.vel_y = 0
        self.player_play.jetpack_fuel = self.player_play.max_fuel

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                if self.modal_active:
                    if event.key == pygame.K_ESCAPE:
                        self.modal_active = None
                    continue
                    
                if self.current_scene == 'play':
                    if event.key in [pygame.K_UP, pygame.K_w, pygame.K_SPACE]:
                        self.player_play.trigger_jump(self)
                    elif event.key in [pygame.K_LSHIFT, pygame.K_l]:
                        self.player_play.trigger_dash(self)
                    elif event.key == pygame.K_k:
                        self.player_play.trigger_attack(self)
                elif self.current_scene == 'hub':
                    if event.key in [pygame.K_UP, pygame.K_w, pygame.K_SPACE]:
                        self.player_hub.trigger_jump(self)
                        
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Clique esquerdo
                    mx, my = event.pos
                    self.handle_clicks(mx, my)

    def handle_clicks(self, mx, my):
        # Gerenciamento de cliques em modais
        if self.modal_active:
            # Fechar modal clicando no X (canto superior direito)
            # Todo modal tem largura 400x300 centralizado
            rx = WIDTH // 2 - 200
            ry = HEIGHT // 2 - 150
            if rx + 370 <= mx <= rx + 390 and ry + 10 <= my <= ry + 30:
                self.modal_active = None
                self.play_sound('collect')
                return
                
            if self.modal_active == 'config':
                # Clique em controle de som
                if ry + 75 <= my <= ry + 95: # Música volume slider
                    self.volume_music = max(0.0, min(1.0, (mx - (rx + 180)) / 150))
                elif ry + 115 <= my <= ry + 135: # SFX slider
                    self.volume_sfx = max(0.0, min(1.0, (mx - (rx + 180)) / 150))
                elif ry + 155 <= my <= ry + 175: # Dificuldade select
                    if rx + 180 <= mx <= rx + 330:
                        self.difficulty = 'hard' if self.difficulty == 'normal' else 'normal'
                elif ry + 195 <= my <= ry + 215: # Mostrar Controles switch
                    if rx + 280 <= mx <= rx + 330:
                        self.show_touch_controls = not self.show_touch_controls
                elif ry + 240 <= my <= ry + 280: # Botão Confirmar
                    if rx + 100 <= mx <= rx + 300:
                        self.modal_active = None
                        self.play_sound('collect')
                return
            elif self.modal_active == 'controls':
                return
            elif self.modal_active == 'briefing':
                # Botões de altura 30 do terminal de viagem estelar
                if "Viagem" in self.briefing_data["title"]:
                    if ry + 65 <= my <= ry + 95: # Cristal Prime
                        self.start_planet('cristal')
                    elif ry + 105 <= my <= ry + 135: # Inferno X
                        if self.collected_fuel >= 3 or 'inferno' in self.unlocked_planets:
                            self.start_planet('inferno')
                    elif ry + 145 <= my <= ry + 175: # Verdantis
                        if self.collected_fuel >= 6 or 'verdantis' in self.unlocked_planets:
                            self.start_planet('verdantis')
                    elif ry + 185 <= my <= ry + 215: # Umbra Void
                        if self.collected_fuel >= 8 or 'umbra' in self.unlocked_planets:
                            self.start_planet('umbra')
                    elif ry + 235 <= my <= ry + 265: # Cancelar
                        self.modal_active = None
                        self.play_sound('collect')
                else:
                    # Retorno ao menu na vitória
                    if ry + 210 <= my <= ry + 250:
                        self.modal_active = None
                        self.current_scene = 'menu'
                        self.play_sound('collect')
                return
        # Cliques no Menu Principal
        if self.current_scene == 'menu':
            # Posicionamento lateral direito: x de 450 a 730
            # Iniciar missão
            if 480 <= mx <= 720 and 220 <= my <= 260:
                self.current_scene = 'hub'
                self.play_sound('collect')
            # Controles
            elif 480 <= mx <= 720 and 280 <= my <= 320:
                self.modal_active = 'controls'
                self.play_sound('collect')
            # Configurações
            elif 480 <= mx <= 720 and 340 <= my <= 380:
                self.modal_active = 'config'
                self.play_sound('collect')
                
        # Cliques no HUD de Jogo
        elif self.current_scene in ['hub', 'play']:
            # Botão de Configuração no HUD (x: 720, y: 16, w: 30, h: 30)
            if 720 <= mx <= 750 and 16 <= my <= 46:
                self.modal_active = 'config'
                self.play_sound('collect')
            # Botão de Tela Cheia no HUD (x: 755, y: 16, w: 30, h: 30)
            elif 755 <= mx <= 785 and 16 <= my <= 46:
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
                else:
                    pygame.display.set_mode((WIDTH, HEIGHT))
                self.play_sound('collect')
                
            # Cliques nos botões touch simulados
            if self.show_touch_controls:
                # Converter coordenadas locais com base no scroll
                pass

    def start_planet(self, planet_key):
        self.modal_active = None
        self.current_scene = 'play'
        self.current_planet = planet_key
        if planet_key not in self.unlocked_planets:
            self.unlocked_planets.append(planet_key)
        self.collected_fuel = 0
        self.active_checkpoint = (100, 350, "Setor de Queda")
        self.init_play()
        self.play_sound('collect')

    def update(self):
        # Atualizar música tema
        self.run_retro_music()
        
        # Se algum modal de menu estiver aberto, congela a física
        if self.modal_active:
            return
            
        # Temporizador de shake de câmera
        if self.camera_shake_timer > 0:
            self.camera_shake_timer -= 1
            
        # Atualizar partículas
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.15 # Gravidade leve nas partículas
            p["life"] -= 1
            p["alpha"] = int((p["life"] / 40.0) * 255)
            if p["life"] <= 0:
                self.particles.remove(p)
                
        # CENA: Estação Espacial HUB
        if self.current_scene == 'hub':
            keys = pygame.key.get_pressed()
            self.player_hub.get_input(keys, self)
            self.player_hub.update(self.hub_platforms, [], [], self)
            
            # Câmera estática no Hub
            self.camera_x = 0
            
            # Interação com o Terminal de Viagem Estelar
            if self.player_hub.hitbox.colliderect(self.hub_terminal.rect):
                self.modal_active = 'briefing'
                self.briefing_data = {
                    "title": "🛰️ Terminal de Viagem Estelar",
                    "desc": "Selecione o planeta destino para iniciar a missão de busca:",
                    "img": None
                }
                # Afasta ligeiramente o player para não triggar em loop ao fechar
                self.player_hub.hitbox.x = 320
                
        # CENA: Exploração Planetária
        elif self.current_scene == 'play':
            keys = pygame.key.get_pressed()
            
            # Se controles virtuais estiverem ativos e mouse pressionado
            if self.show_touch_controls:
                m_pressed = pygame.mouse.get_pressed()[0]
                mx, my = pygame.mouse.get_pos()
                self.touch_state = {"left": False, "right": False, "jump": False, "jetpack": False}
                if m_pressed:
                    if self.touch_buttons["left"].collidepoint(mx, my):
                        self.touch_state["left"] = True
                    if self.touch_buttons["right"].collidepoint(mx, my):
                        self.touch_state["right"] = True
                    if self.touch_buttons["jump"].collidepoint(mx, my):
                        self.touch_state["jump"] = True
                    if self.touch_buttons["jetpack"].collidepoint(mx, my):
                        self.touch_state["jetpack"] = True
                        
            # Passar entrada física ou virtual para o jogador
            self.player_play.get_input(keys, self)
            if self.show_touch_controls:
                if self.touch_state["left"]:
                    self.player_play.vel_x = -5.0
                    self.player_play.facing_right = False
                elif self.touch_state["right"]:
                    self.player_play.vel_x = 5.0
                    self.player_play.facing_right = True
                if self.touch_state["jump"] and self.player_play.on_ground:
                    self.player_play.trigger_jump(self)
                if self.touch_state["jetpack"] and not self.player_play.on_ground and self.player_play.jetpack_fuel > 0:
                    self.player_play.vel_y = -4.5
                    self.player_play.jetpack_fuel -= 1.2
                    self.create_particles(self.player_play.hitbox.centerx, self.player_play.hitbox.bottom, (249, 115, 22), 2)
            
            self.player_play.update(self.play_platforms, self.solid_blocks, self.mystery_blocks, self)
            
            # Atualizar inimigos
            self.enemies.update(self.play_platforms, self.solid_blocks)
            self.fuels.update()
            
            # Câmera suave seguindo o jogador (Centralizado a 400px horizontalmente)
            target_camera_x = self.player_play.hitbox.centerx - 400
            # Limites da câmera (Fase tem 2400px, largura da janela é 800px)
            if target_camera_x < 0:
                target_camera_x = 0
            elif target_camera_x > 1600:
                target_camera_x = 1600
            # Lerp de interpolação da câmera
            self.camera_x += (target_camera_x - self.camera_x) * 0.1
            
            # Morte e Respawn suave
            if self.player_play.health <= 0:
                self.respawn_player()
                
            # Coleta de combustível naves amarelas
            collected = pygame.sprite.spritecollide(self.player_play, self.fuels, True)
            if collected:
                for f in collected:
                    self.play_sound('collect')
                    self.create_particles(f.rect.centerx, f.rect.centery, COLOR_ACCENT, 20)
                    self.collected_fuel += 1
                    
            # Ativação de checkpoint
            if self.player_play.hitbox.colliderect(self.play_checkpoint.rect) and not self.play_checkpoint.active:
                self.play_checkpoint.activate(self)
                self.active_checkpoint = (self.play_checkpoint.rect.x, self.play_checkpoint.rect.y - 20, "Setor Cristalino")
                
            # Fim da fase (Decolar na nave vermelha com 9 combustíveis)
            if self.player_play.hitbox.colliderect(self.play_spaceship.rect):
                if self.collected_fuel >= 9:
                    self.play_sound('collect')
                    self.current_scene = 'menu' # Retorna vitorioso
                    self.modal_active = 'briefing'
                    self.briefing_data = {
                        "title": "🎉 Missão Concluída!",
                        "desc": "Incrível! Cadu e o astronauta gif consertaram os reatores e decolaram com sucesso!",
                        "img": None
                    }
                else:
                    # Avisa o jogador na tela
                    pass

    def draw(self):
        # Efeito de tremor de câmera
        cam_offset_x = 0
        cam_offset_y = 0
        if self.camera_shake_timer > 0:
            cam_offset_x = random.randint(-self.camera_shake_intensity, self.camera_shake_intensity)
            cam_offset_y = random.randint(-self.camera_shake_intensity, self.camera_shake_intensity)
            
        # Limpar tela
        self.screen.fill(COLOR_BG)
        
        # 1. RENDERIZAR TELA DE MENU PRINCIPAL (CAPA)
        if self.current_scene == 'menu':
            # Desenha a capa centralizada com contain
            if not self.fallback_cover:
                cw = self.cover_img.get_width()
                cx = (WIDTH - cw) // 2
                self.screen.blit(self.cover_img, (cx, 0))
            else:
                # Fallback visual caso não carregue a capa cover.jpg
                pygame.draw.rect(self.screen, (15, 23, 42), (200, 50, 400, 420))
                
            # Menu Lateral Direito (Estilo Glassmorphism translúcido)
            # Posicionado na área de faixa preta lateral
            menu_bg = pygame.Surface((320, 400), pygame.SRCALPHA)
            menu_bg.fill((15, 23, 42, 200)) # Preto translúcido
            pygame.draw.rect(menu_bg, (255, 255, 255, 30), (0, 0, 320, 400), 1) # Borda
            self.screen.blit(menu_bg, (450, 60))
            
            # Texto do Painel
            txt_subtitle = self.font_hud.render("MISSÃO GALÁCTICA", True, COLOR_ACCENT)
            txt_title = self.font_title.render("PAINEL DE OPERAÇÕES", True, (255, 255, 255))
            self.screen.blit(txt_subtitle, (530, 90))
            self.screen.blit(txt_title, (485, 120))
            
            # Botões do Menu
            self.draw_button("🚀 INICIAR MISSÃO", (480, 220, 240, 40), COLOR_NEON_BLUE)
            self.draw_button("🎮 CONTROLES", (480, 280, 240, 40), (255, 255, 255, 40))
            self.draw_button("⚙️ CONFIGURAÇÕES", (480, 340, 240, 40), (255, 255, 255, 40))
            
        # 2. RENDERIZAR HUB (ESTAÇÃO ESPACIAL)
        elif self.current_scene == 'hub':
            # Desenha fundo
            if not self.fallback_bg:
                self.screen.blit(self.bg_textures['hub'], (0, 0))
            
            # Desenhar Terminal e Nave
            self.screen.blit(self.hub_terminal.image, self.hub_terminal.rect)
            self.screen.blit(self.hub_spaceship.image, self.hub_spaceship.rect)
            
            # Desenhar Chão
            for tile in self.hub_platforms:
                self.screen.blit(tile.image, tile.rect)
                
            # Desenhar Player
            self.screen.blit(self.player_hub.image, self.player_hub.rect)
            
            # HUD Superior
            self.draw_hud("Estação Espacial", self.player_hub)
            
        # 3. RENDERIZAR PLAYSCENE (PLANETA EXPLORAÇÃO)
        elif self.current_scene == 'play':
            # Desenha Fundo Infinito Parallax baseado no planeta atual
            if not self.fallback_bg:
                bg_key = self.current_planet
                bg_tex = self.bg_textures.get(bg_key, self.bg_textures['cristal'])
                bx = -int((self.camera_x * 0.15) % WIDTH)
                self.screen.blit(bg_tex, (bx, 0))
                self.screen.blit(bg_tex, (bx + WIDTH, 0))
                
            # Desenhar Checkpoint
            cp_rx = self.play_checkpoint.rect.x - int(self.camera_x) + cam_offset_x
            self.screen.blit(self.play_checkpoint.image, (cp_rx, self.play_checkpoint.rect.y + cam_offset_y))
            
            # Desenhar Nave Vermelha de Decolagem
            ship_rx = self.play_spaceship.rect.x - int(self.camera_x) + cam_offset_x
            self.screen.blit(self.play_spaceship.image, (ship_rx, self.play_spaceship.rect.y + cam_offset_y))
            
            # Desenhar Blocos e Plataformas
            for tile in list(self.play_platforms) + list(self.solid_blocks) + list(self.mystery_blocks):
                rx = tile.rect.x - int(self.camera_x) + cam_offset_x
                ry = tile.rect.y + cam_offset_y
                self.screen.blit(tile.image, (rx, ry))
                
            # Desenhar Combustíveis flutuantes
            for fuel in self.fuels:
                rx = fuel.rect.x - int(self.camera_x) + cam_offset_x
                ry = fuel.rect.y + cam_offset_y
                self.screen.blit(fuel.image, (rx, ry))
                
            # Desenhar Inimigos
            for enemy in self.enemies:
                rx = enemy.rect.x - int(self.camera_x) + cam_offset_x
                ry = enemy.rect.y + cam_offset_y
                self.screen.blit(enemy.image, (rx, ry))
                
            # Desenhar Player
            prx = self.player_play.rect.x - int(self.camera_x) + cam_offset_x
            pry = self.player_play.rect.y + cam_offset_y
            self.screen.blit(self.player_play.image, (prx, pry))
            
            # Se estiver atacando, desenha área de ataque
            if self.player_play.is_attacking:
                ax = prx + 32 if self.player_play.facing_right else prx - 22
                pygame.draw.circle(self.screen, COLOR_NEON_RED, (ax + 10, pry + 25), 15, 2)
                
            # HUD Superior
            self.draw_hud("Cristal Prime", self.player_play)
            
            # Mostrar aviso flutuante se encostar na nave sem combustíveis
            if self.player_play.hitbox.colliderect(self.play_spaceship.rect) and self.collected_fuel < 9:
                txt = self.font_body.render("Colete os 9 tanques de combustível!", True, COLOR_NEON_RED)
                # Fundo preto atrás do aviso
                pygame.draw.rect(self.screen, COLOR_BG, (ship_rx - 40, self.play_spaceship.rect.y - 25, 210, 20))
                self.screen.blit(txt, (ship_rx - 35, self.play_spaceship.rect.y - 23))

        # Desenhar Partículas
        for p in self.particles:
            rx = p["x"] - (int(self.camera_x) if self.current_scene == 'play' else 0) + cam_offset_x
            ry = p["y"] + cam_offset_y
            # Desenhar pequenos pixels
            pygame.draw.rect(self.screen, p["color"], (rx, ry, 4, 4))

        # Desenhar Controles Virtuais de Toque se ativado
        if self.current_scene == 'play' and self.show_touch_controls:
            self.draw_touch_controls()

        # Renderizar Modais por cima de tudo
        if self.modal_active:
            self.draw_modal()

        # Apresentar
        pygame.display.flip()

    def draw_button(self, text, rect_tuple, color):
        rect = pygame.Rect(rect_tuple)
        btn_surface = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        
        # Cor de base e borda neon
        btn_surface.fill((255, 255, 255, 12) if len(color) > 3 or color[0] == 255 else (color[0], color[1], color[2], 50))
        pygame.draw.rect(btn_surface, color[:3], (0, 0, rect.w, rect.h), 2, border_radius=6)
        self.screen.blit(btn_surface, (rect.x, rect.y))
        
        # Texto centralizado
        txt = self.font_btn.render(text, True, (255, 255, 255))
        tx = rect.x + (rect.w - txt.get_width()) // 2
        ty = rect.y + (rect.h - txt.get_height()) // 2
        self.screen.blit(txt, (tx, ty))

    def draw_hud(self, planet_name, player_entity):
        # Barra superior HUD (Altura 54px)
        hud_bg = pygame.Surface((WIDTH, 54), pygame.SRCALPHA)
        hud_bg.fill((15, 23, 42, 190)) # Glassmorphism
        pygame.draw.line(hud_bg, (255, 255, 255, 20), (0, 53), (WIDTH, 53), 1)
        self.screen.blit(hud_bg, (0, 0))
        
        # Avatar do gif no canto esquerdo
        pygame.draw.circle(self.screen, COLOR_NEON_BLUE, (30, 27), 18, 2)
        if self.player_face:
            self.screen.blit(self.player_face, (11, 8))
        else:
            pygame.draw.circle(self.screen, (255, 255, 255), (30, 27), 14)
            
        # Infos de nome e cargo
        txt_name = self.font_hud.render("gif", True, (255, 255, 255))
        txt_role = self.font_body.render("Astronauta ES", True, COLOR_NEON_BLUE)
        self.screen.blit(txt_name, (56, 10))
        self.screen.blit(txt_role, (56, 26))
        
        # Elemento: Localização
        self.draw_hud_item("LOCALIZAÇÃO", planet_name, (180, 8, 140, 38), COLOR_NEON_BLUE)
        
        # Elemento: Combustíveis
        self.draw_hud_item("COMBUSTÍVEL", f"{self.collected_fuel} / 9", (340, 8, 120, 38), COLOR_ACCENT)
        
        # Elemento: Barra do Jetpack
        pygame.draw.rect(self.screen, (255, 255, 255, 10), (480, 25, 90, 8))
        fuel_w = int(90 * (player_entity.jetpack_fuel / player_entity.max_fuel))
        pygame.draw.rect(self.screen, COLOR_NEON_BLUE, (480, 25, fuel_w, 8))
        txt_jet_lbl = self.font_body.render("JETPACK", True, (148, 163, 184))
        self.screen.blit(txt_jet_lbl, (480, 8))
        
        # Elemento: Checkpoint ativo
        self.draw_hud_item("SINAL ATIVO", self.active_checkpoint[2], (590, 8, 120, 38), COLOR_NEON_GREEN)
        
        # Botões de Pause/Engrenagem e Fullscreen (Direita)
        # Engrenagem
        pygame.draw.rect(self.screen, (255, 255, 255, 15), (720, 12, 30, 30), border_radius=4)
        txt_gear = self.font_hud.render("G", True, (255, 255, 255)) # G de Gear
        self.screen.blit(txt_gear, (729, 18))
        
        # Fullscreen TV
        pygame.draw.rect(self.screen, (255, 255, 255, 15), (755, 12, 30, 30), border_radius=4)
        txt_tv = self.font_hud.render("F", True, (255, 255, 255)) # F de Fullscreen
        self.screen.blit(txt_tv, (765, 18))

    def draw_hud_item(self, label, value, rect_tuple, color):
        x, y, w, h = rect_tuple
        pygame.draw.rect(self.screen, (255, 255, 255, 8), (x, y, w, h), border_radius=6)
        pygame.draw.rect(self.screen, color, (x, y, w, h), 1, border_radius=6)
        
        txt_lbl = self.font_body.render(label, True, (148, 163, 184))
        txt_val = self.font_hud.render(value, True, color)
        
        self.screen.blit(txt_lbl, (x + 8, y + 4))
        self.screen.blit(txt_val, (x + 8, y + 18))

    def draw_touch_controls(self):
        for name, rect in self.touch_buttons.items():
            btn_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            # Desenha circulo translúcido
            color = COLOR_NEON_BLUE if name != 'attack' else COLOR_NEON_RED
            btn_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(btn_surf, (color[0], color[1], color[2], 100), (27, 27), 27)
            pygame.draw.circle(btn_surf, color, (27, 27), 27, 2)
            self.screen.blit(btn_surf, (rect.x, rect.y))
            
            # Seta/Ícone
            labels = {"left": "<-", "right": "->", "jump": "^", "jetpack": "J", "attack": "X"}
            txt = self.font_hud.render(labels.get(name, ""), True, (255, 255, 255))
            tx = rect.x + (rect.w - txt.get_width()) // 2
            ty = rect.y + (rect.h - txt.get_height()) // 2
            self.screen.blit(txt, (tx, ty))

    def draw_modal(self):
        # Escurecer fundo da tela
        dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 180))
        self.screen.blit(dim, (0, 0))
        
        # Caixa do Modal (Largura 400, Altura 300)
        mw, mh = 400, 300
        mx = (WIDTH - mw) // 2
        my = (HEIGHT - mh) // 2
        
        modal_surf = pygame.Surface((mw, mh), pygame.SRCALPHA)
        modal_surf.fill((15, 23, 42, 235))
        pygame.draw.rect(modal_surf, (255, 255, 255, 30), (0, 0, mw, mh), 2, border_radius=12)
        self.screen.blit(modal_surf, (mx, my))
        
        # Botão fechar (X)
        txt_x = self.font_hud.render("X", True, (148, 163, 184))
        self.screen.blit(txt_x, (mx + 375, my + 12))
        
        # Título
        title_str = ""
        if self.modal_active == 'config':
            title_str = "⚙️ CONFIGURAÇÕES"
        elif self.modal_active == 'controls':
            title_str = "🎮 CONTROLES DO JOGO"
        elif self.modal_active == 'briefing':
            title_str = self.briefing_data["title"]
            
        txt_title = self.font_title.render(title_str, True, COLOR_NEON_BLUE)
        self.screen.blit(txt_title, (mx + 20, my + 15))
        pygame.draw.line(self.screen, (255, 255, 255, 20), (mx + 20, my + 50), (mx + 380, my + 50), 1)
        
        # Conteúdo baseado no tipo de modal
        if self.modal_active == 'config':
            # Linha 1: Música
            txt_mus = self.font_body.render("Volume Música:", True, (255, 255, 255))
            self.screen.blit(txt_mus, (mx + 30, my + 75))
            pygame.draw.rect(self.screen, (255, 255, 255, 20), (mx + 180, my + 80, 150, 8))
            pygame.draw.rect(self.screen, COLOR_NEON_BLUE, (mx + 180, my + 80, int(150 * self.volume_music), 8))
            
            # Linha 2: SFX
            txt_sfx = self.font_body.render("Volume Som (SFX):", True, (255, 255, 255))
            self.screen.blit(txt_sfx, (mx + 30, my + 115))
            pygame.draw.rect(self.screen, (255, 255, 255, 20), (mx + 180, my + 120, 150, 8))
            pygame.draw.rect(self.screen, COLOR_NEON_BLUE, (mx + 180, my + 120, int(150 * self.volume_sfx), 8))
            
            # Linha 3: Dificuldade
            txt_dif = self.font_body.render("Dificuldade:", True, (255, 255, 255))
            self.screen.blit(txt_dif, (mx + 30, my + 155))
            dif_str = "Explorador (Padrão)" if self.difficulty == 'normal' else "Sobrevivência (Dano 2x)"
            self.draw_button(dif_str, (mx + 180, my + 150, 180, 24), COLOR_NEON_BLUE)
            
            # Linha 4: Controles Virtuais
            txt_tcl = self.font_body.render("Controles na Tela:", True, (255, 255, 255))
            self.screen.blit(txt_tcl, (mx + 30, my + 195))
            tcl_str = "LIGADO" if self.show_touch_controls else "DESLIGADO"
            btn_col = COLOR_NEON_GREEN if self.show_touch_controls else COLOR_NEON_RED
            self.draw_button(tcl_str, (mx + 250, my + 190, 80, 24), btn_col)
            
            # Confirmar
            self.draw_button("CONFIRMAR E FECHAR", (mx + 100, my + 245, 200, 35), COLOR_NEON_GREEN)
            
        elif self.modal_active == 'controls':
            controls_list = [
                ("Mover Esquerda / Direita", "A / D ou Seta Esq / Dir"),
                ("Pular / Double Jump", "W ou Seta Cima ou Space"),
                ("Jetpack (Voo temporário)", "Segurar Pulo no ar"),
                ("Dash / Desvio Rápido", "L ou Shift"),
                ("Ataque de Plasma", "K"),
                ("Engrenagem HUD / Sair", "G ou Esc / modal")
            ]
            cy = my + 65
            for desc, key in controls_list:
                t_desc = self.font_body.render(desc, True, (148, 163, 184))
                t_key = self.font_btn.render(key, True, COLOR_NEON_BLUE)
                self.screen.blit(t_desc, (mx + 30, cy))
                self.screen.blit(t_key, (mx + 220, cy))
                cy += 30
                
        elif self.modal_active == 'briefing':
            # Conteúdo do terminal de viagem ou vitória
            txt_desc = self.font_body.render(self.briefing_data["desc"], True, (203, 213, 225))
            self.screen.blit(txt_desc, (mx + 20, my + 65))
            
            if "Viagem" in self.briefing_data["title"]:
                # Desenha botões de viagem alinhados verticalmente de 30px
                self.draw_button("🌍 CRISTAL PRIME (Fase 1)", (mx + 60, my + 65, 280, 30), COLOR_NEON_BLUE)
                
                inf_col = COLOR_NEON_BLUE if (self.collected_fuel >= 3 or 'inferno' in self.unlocked_planets) else (255,255,255,30)
                inf_lbl = "🔥 INFERNO X (Fase 2)" if (self.collected_fuel >= 3 or 'inferno' in self.unlocked_planets) else "🔒 INFERNO X (Requer 3 Naves)"
                self.draw_button(inf_lbl, (mx + 60, my + 105, 280, 30), inf_col)
                
                ver_col = COLOR_NEON_BLUE if (self.collected_fuel >= 6 or 'verdantis' in self.unlocked_planets) else (255,255,255,30)
                ver_lbl = "🍄 VERDANTIS (Fase 3)" if (self.collected_fuel >= 6 or 'verdantis' in self.unlocked_planets) else "🔒 VERDANTIS (Requer 6 Naves)"
                self.draw_button(ver_lbl, (mx + 60, my + 145, 280, 30), ver_col)
                
                umb_col = COLOR_NEON_BLUE if (self.collected_fuel >= 8 or 'umbra' in self.unlocked_planets) else (255,255,255,30)
                umb_lbl = "🌀 UMBRA VOID (Fase 4)" if (self.collected_fuel >= 8 or 'umbra' in self.unlocked_planets) else "🔒 UMBRA VOID (Requer 8 Naves)"
                self.draw_button(umb_lbl, (mx + 60, my + 185, 280, 30), umb_col)
                
                self.draw_button("CANCELAR", (mx + 140, my + 235, 120, 30), COLOR_NEON_RED)
            else:
                # Vitória de decolagem
                txt_vit = self.font_btn.render("PROCESSO DE DOBRA CONCLUÍDO!", True, COLOR_NEON_GREEN)
                self.screen.blit(txt_vit, (mx + 60, my + 140))
                self.draw_button("VOLTAR AO MENU", (mx + 100, my + 210, 200, 40), COLOR_NEON_GREEN)

if __name__ == "__main__":
    game = Game()
    while game.running:
        game.process_events()
        game.update()
        game.draw()
        game.clock.tick(FPS)
    pygame.quit()
    sys.exit()
