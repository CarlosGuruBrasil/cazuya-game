import pygame
import math
import random

# Dimensões do jogo
WIDTH = 800
HEIGHT = 520

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, spritesheet_path):
        super().__init__()
        
        # Carregar animações do spritesheet (5 frames horizontais de 185x305 px)
        self.frames = []
        self.fallback = False
        
        try:
            sheet = pygame.image.load(spritesheet_path).convert_alpha()
            frame_w = 185
            frame_h = 305
            for i in range(5):
                frame_rect = pygame.Rect(i * frame_w, 0, frame_w, frame_h)
                frame = sheet.subsurface(frame_rect)
                # Redimensionar para tamanho ideal no jogo (30x50px)
                frame_scaled = pygame.transform.scale(frame, (30, 50))
                self.frames.append(frame_scaled)
        except Exception as e:
            print(f"Erro ao carregar spritesheet do astronauta, usando fallback visual: {e}")
            self.fallback = True
            
        self.image_idx = 0
        if self.fallback:
            self.image = pygame.Surface((30, 50), pygame.SRCALPHA)
            pygame.draw.rect(self.image, (14, 165, 233), (0, 0, 30, 50)) # Retângulo ciano
            pygame.draw.circle(self.image, (255, 255, 255), (15, 15), 10) # Visor branco
        else:
            self.image = self.frames[0]
            
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        # Bounding box interna menor para colisões mais justas e suaves
        self.hitbox = pygame.Rect(x + 3, y + 2, 24, 46)
        
        # Física
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        
        # Habilidades
        self.health = 100
        self.max_health = 100
        self.jetpack_fuel = 100.0
        self.max_fuel = 100.0
        self.is_dashing = False
        self.dash_timer = 0
        self.dash_cooldown = 0
        self.can_double_jump = False
        self.on_wall = False
        self.wall_slide = False
        self.is_attacking = False
        self.attack_timer = 0
        
        # Animação
        self.animation_timer = 0
        
    def get_input(self, keys, game_instance):
        if self.health <= 0 or self.is_dashing:
            return
            
        # Movimento Horizontal
        speed = 5.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -speed
            self.facing_right = False
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = speed
            self.facing_right = True
        else:
            self.vel_x = 0
            
        # Pulo e Jetpack
        # O pulo normal e pulo duplo são disparados por eventos de clique único (keydown), tratados no main.py.
        # O Jetpack (segurar pulo no ar) é contínuo por pressão de tecla:
        jump_key = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
        if jump_key and not self.on_ground and self.jetpack_fuel > 0:
            self.vel_y = -4.5
            self.jetpack_fuel -= 1.2
            # Efeito visual de fogo do Jetpack (Partículas laranjas)
            game_instance.create_particles(self.hitbox.centerx, self.hitbox.bottom, (249, 115, 22), 2)
            if random.random() < 0.1:
                game_instance.play_sound('jump')
        elif self.on_ground and self.jetpack_fuel < self.max_fuel:
            self.jetpack_fuel += 2.0
            if self.jetpack_fuel > self.max_fuel:
                self.jetpack_fuel = self.max_fuel

    def trigger_jump(self, game_instance):
        if self.health <= 0:
            return
            
        # Pulo no chão ou Wall Jump
        if self.on_ground:
            self.vel_y = -10.5
            self.on_ground = False
            self.can_double_jump = True
            game_instance.play_sound('jump')
        elif self.wall_slide:
            # Pulo na parede (joga o player para a direção oposta)
            self.vel_y = -9.5
            self.vel_x = -7 if self.facing_right else 7
            self.facing_right = not self.facing_right
            self.wall_slide = False
            game_instance.play_sound('jump')
            game_instance.create_particles(self.hitbox.centerx, self.hitbox.centery, (14, 165, 233), 10)
        # Pulo Duplo (Requer ter resgatado pelo menos 2 naves / combustíveis na fase)
        elif self.can_double_jump and game_instance.collected_fuel >= 2:
            self.vel_y = -9.0
            self.can_double_jump = False
            game_instance.play_sound('jump')
            game_instance.create_particles(self.hitbox.centerx, self.hitbox.bottom, (14, 165, 233), 12)
            
    def trigger_dash(self, game_instance):
        if self.health <= 0 or self.dash_cooldown > 0 or self.is_dashing:
            return
        # Dash desbloqueia com pelo menos 4 naves/combustíveis
        if game_instance.collected_fuel >= 4:
            self.is_dashing = True
            self.dash_timer = 12 # 12 frames a 60 FPS = 0.2s
            self.dash_cooldown = 45 # cooldown de 0.75s
            self.vel_y = 0
            self.vel_x = 16 if self.facing_right else -16
            game_instance.play_sound('dash')
            game_instance.create_particles(self.hitbox.centerx, self.hitbox.centery, (14, 165, 233), 15)

    def trigger_attack(self, game_instance):
        if self.health <= 0 or self.is_attacking:
            return
        self.is_attacking = True
        self.attack_timer = 15 # 0.25s de ataque
        game_instance.play_sound('attack')
        # Partículas de plasma na direção do ataque
        px = self.hitbox.right + 10 if self.facing_right else self.hitbox.left - 10
        game_instance.create_particles(px, self.hitbox.centery, (239, 68, 68), 10)

    def update(self, platforms, solid_blocks, mystery_blocks, game_instance):
        if self.health <= 0:
            self.vel_x = 0
            self.apply_gravity()
            self.move_and_collide(platforms, solid_blocks, mystery_blocks, game_instance)
            return

        # Cooldowns
        if self.dash_cooldown > 0:
            self.dash_cooldown -= 1
        if self.attack_timer > 0:
            self.attack_timer -= 1
            if self.attack_timer == 0:
                self.is_attacking = False
                
        # Gerenciamento de Dash
        if self.is_dashing:
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.vel_x = 0
        else:
            self.apply_gravity()
            
        # Movimentação física e Colisões
        self.move_and_collide(platforms, solid_blocks, mystery_blocks, game_instance)
        
        # Limites laterais da fase (Fase tem 2400px de largura)
        if self.hitbox.left < 0:
            self.hitbox.left = 0
            self.vel_x = 0
        elif self.hitbox.right > 2400:
            self.hitbox.right = 2400
            self.vel_x = 0
            
        # Atualizar a posição do rect baseado na hitbox
        self.rect.x = self.hitbox.x - 3
        self.rect.y = self.hitbox.y - 2
        
        # Morte por queda no abismo
        if self.hitbox.y > HEIGHT - 5:
            self.take_damage(100, game_instance)
            
        # Atualizar Animação
        self.animate()

    def apply_gravity(self):
        # Gravidade reduzida se estiver fazendo wall slide
        if self.wall_slide and self.vel_y > 0:
            self.vel_y += 0.18 # Gravidade leve
            if self.vel_y > 1.8:
                self.vel_y = 1.8
        else:
            self.vel_y += 0.55 # Gravidade padrão
            if self.vel_y > 11:
                self.vel_y = 11

    def move_and_collide(self, platforms, solid_blocks, mystery_blocks, game_instance):
        # Colisão Horizontal
        self.hitbox.x += self.vel_x
        
        # Lista combinada para colisões
        blocks = list(platforms) + list(solid_blocks) + list(mystery_blocks)
        
        self.on_wall = False
        for block in blocks:
            if self.hitbox.colliderect(block.rect):
                if self.vel_x > 0:
                    self.hitbox.right = block.rect.left
                    self.on_wall = True
                elif self.vel_x < 0:
                    self.hitbox.left = block.rect.right
                    self.on_wall = True
                self.vel_x = 0

        # Colisão Vertical
        self.hitbox.y += self.vel_y
        self.on_ground = False
        
        for block in blocks:
            if self.hitbox.colliderect(block.rect):
                if self.vel_y > 0:
                    self.hitbox.bottom = block.rect.top
                    self.on_ground = True
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.hitbox.top = block.rect.bottom
                    self.vel_y = 0
                    
                    # Cabeçada no bloco surpresa
                    if isinstance(block, Tile) and block.tile_type == 'mystery':
                        if not block.hit:
                            block.hit_block(game_instance)

        # Detectar Wall Slide (se no ar, caindo e encostando em blocos laterais)
        if self.on_wall and not self.on_ground and self.vel_y > 0:
            self.wall_slide = True
        else:
            self.wall_slide = False

    def take_damage(self, amount, game_instance):
        if self.health <= 0:
            return
            
        if game_instance.difficulty == 'hard':
            amount *= 2
            
        self.health -= amount
        game_instance.play_sound('hurt')
        game_instance.shake_camera(8)
        
        if self.health <= 0:
            self.health = 0
            game_instance.create_particles(self.hitbox.centerx, self.hitbox.centery, (239, 68, 68), 20)
            
    def animate(self):
        if self.fallback:
            return
            
        self.animation_timer += 1
        
        # Seleção de frame baseado no estado
        if not self.on_ground:
            if self.wall_slide:
                self.image_idx = 3 # Pulo/Slide
            elif self.vel_y < 0:
                self.image_idx = 3 # Pulo
            else:
                self.image_idx = 4 # Queda
        elif self.vel_x != 0:
            # Frame 1 e 2 para animação de corrida
            if self.animation_timer % 8 == 0:
                self.image_idx = 1 if self.image_idx == 2 else 2
        else:
            self.image_idx = 0 # Idle
            
        frame_img = self.frames[self.image_idx]
        
        # Espelhar se estiver virado para a esquerda
        if not self.facing_right:
            frame_img = pygame.transform.flip(frame_img, True, False)
            
        # Se estiver atacando ou com dano, aplica cor/tint
        if self.is_attacking:
            # Filtro avermelhado leve
            tint = pygame.Surface(frame_img.get_size(), pygame.SRCALPHA)
            tint.fill((239, 68, 68, 80))
            frame_img = frame_img.copy()
            frame_img.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
        self.image = frame_img


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, tile_type, image_path=None):
        super().__init__()
        self.tile_type = tile_type
        self.hit = False
        
        # Fallback de cor por tipo de bloco
        colors = {
            'ground': (75, 85, 99),   # Cinza escuro
            'solid': (30, 41, 59),    # Metal
            'mystery': (245, 158, 11)  # Dourado
        }
        
        self.fallback = False
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (40, 40))
            except Exception as e:
                print(f"Erro ao carregar tile {image_path}, usando fallback: {e}")
                self.fallback = True
        else:
            self.fallback = True
            
        if self.fallback:
            self.image = pygame.Surface((40, 40))
            self.image.fill(colors.get(tile_type, (128, 128, 128)))
            pygame.draw.rect(self.image, (255, 255, 255), (0, 0, 40, 40), 1) # Borda
            
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
    def hit_block(self, game_instance):
        if self.tile_type == 'mystery' and not self.hit:
            self.hit = True
            game_instance.play_sound('collect')
            game_instance.create_particles(self.rect.centerx, self.rect.bottom, (245, 158, 11), 15)
            game_instance.collected_fuel += 1
            
            # Efeito de tint escuro no bloco golpeado
            if not self.fallback:
                tint = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
                tint.fill((100, 100, 100, 150))
                self.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                self.image.fill((113, 113, 122)) # Cinza opaco
                pygame.draw.rect(self.image, (255, 255, 255), (0, 0, 40, 40), 1)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type, image_path=None):
        super().__init__()
        self.enemy_type = enemy_type
        self.direction = -1
        self.time = 0
        self.start_y = y
        
        self.fallback = False
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (32, 32) if enemy_type == 'slime' else (36, 30))
            except Exception as e:
                print(f"Erro ao carregar inimigo {image_path}, usando fallback: {e}")
                self.fallback = True
        else:
            self.fallback = True
            
        if self.fallback:
            self.image = pygame.Surface((32, 32) if enemy_type == 'slime' else (36, 30))
            color = (239, 68, 68) if enemy_type == 'slime' else (168, 85, 247)
            self.image.fill(color)
            pygame.draw.rect(self.image, (255, 255, 255), self.image.get_rect(), 1)
            
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.vel_x = -1.5 if enemy_type == 'slime' else 0
        
    def update(self, platforms, solid_blocks):
        self.time += 0.05
        
        if self.enemy_type == 'slime':
            # Movimento Horizontal simples de patrulha
            self.rect.x += self.vel_x
            
            # Checar colisão horizontal com o cenário para virar
            blocks = list(platforms) + list(solid_blocks)
            for block in blocks:
                if self.rect.colliderect(block.rect):
                    self.vel_x *= -1
                    self.direction *= -1
                    self.rect.x += self.vel_x
                    if not self.fallback:
                        self.image = pygame.transform.flip(self.image, True, False)
                    break
        elif self.enemy_type == 'drone':
            # Movimento senoidal no ar (flutuação)
            self.rect.y = self.start_y + int(math.sin(self.time) * 25)


class FuelCell(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path=None):
        super().__init__()
        self.start_y = y
        self.time = random.random() * 10
        
        self.fallback = False
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (36, 36))
            except Exception as e:
                self.fallback = True
        else:
            self.fallback = True
            
        if self.fallback:
            self.image = pygame.Surface((30, 30))
            self.image.fill((245, 158, 11))
            pygame.draw.circle(self.image, (255, 255, 255), (15, 15), 5)
            
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
    def update(self):
        # Flutuação
        self.time += 0.06
        self.rect.y = self.start_y + int(math.sin(self.time) * 8)


class Checkpoint(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path=None):
        super().__init__()
        self.active = False
        
        self.fallback = False
        if image_path:
            try:
                self.original_image = pygame.image.load(image_path).convert_alpha()
                self.original_image = pygame.transform.scale(self.original_image, (40, 80))
                self.image = self.original_image.copy()
            except Exception as e:
                self.fallback = True
        else:
            self.fallback = True
            
        if self.fallback:
            self.image = pygame.Surface((30, 60))
            self.image.fill((100, 116, 139))
            pygame.draw.rect(self.image, (255, 255, 255), (0, 0, 30, 60), 1)
            
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
    def activate(self, game_instance):
        if not self.active:
            self.active = True
            game_instance.play_sound('checkpoint')
            game_instance.create_particles(self.rect.centerx, self.rect.centery, (16, 185, 129), 20)
            
            # Filtro esverdeado para mostrar ativado
            if not self.fallback:
                tint = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
                tint.fill((16, 185, 129, 100)) # Verde
                self.image = self.original_image.copy()
                self.image.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            else:
                self.image.fill((16, 185, 129))
                pygame.draw.rect(self.image, (255, 255, 255), (0, 0, 30, 60), 1)


class SpaceshipRed(pygame.sprite.Sprite):
    def __init__(self, x, y, image_path=None):
        super().__init__()
        
        self.fallback = False
        if image_path:
            try:
                self.image = pygame.image.load(image_path).convert_alpha()
                self.image = pygame.transform.scale(self.image, (120, 120))
            except Exception as e:
                self.fallback = True
        else:
            self.fallback = True
            
        if self.fallback:
            self.image = pygame.Surface((100, 100))
            self.image.fill((239, 68, 68))
            pygame.draw.rect(self.image, (255, 255, 255), (0, 0, 100, 100), 2)
            
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
