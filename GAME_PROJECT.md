# Especificação Técnica: Cadu's Cosmic Quest: The Adventures of GIF (Pygame)

Especificação de arquitetura e diretrizes de desenvolvimento para o jogo de plataforma 2D premium em Pygame.

## Perfil do Desenvolvedor
Especialista em jogos 2D usando Python 3 e a biblioteca Pygame, focado em código modular, OOP rigorosa e performance estável a 60 FPS.

## Diretrizes de Código
1. **Estrutura OOP**: Divisão modular do projeto em classes:
   - `Game` (main.py): Máquina de estados, loop de controle, chiptunes e renderização do HUD.
   - `Player` (sprites.py): Astronauta gif com movimento, física, habilidades (jetpack, dash, wall jump, combos) e animações.
   - `Tile`, `Enemy`, `FuelCell`, `Checkpoint` (sprites.py): Entidades e obstáculos com colisão física.
2. **Loop do Jogo Rigoroso**: Separação estrita do ciclo de frames nos métodos:
   - `process_events()`: Leitura de teclado, cliques de botões e fechamento do jogo.
   - `update()`: Cálculos físicos, movimentação, colisões e temporizadores.
   - `draw()`: Desenho de cenários, fundos parallax, sprites, partículas e HUD.
3. **Gerenciamento de Recursos**: Carregamento único de imagens (`pygame.image.load`) e inicialização do áudio no início. Nenhum carregamento em tempo de execução dentro de loops.
4. **Tratamento de Erros de Recursos**: Se qualquer asset de imagem ou som falhar ao carregar, usar formas geométricas simples (retângulos/círculos) coloridos como fallback imediato para garantir estabilidade.
5. **Frame Rate**: Limitação estrita a 60 FPS usando `pygame.time.Clock().tick(60)`.
