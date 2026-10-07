"""Tela do jogo: menu e partida contra os bots.

Rode com: python main.py
As regras ficam em regras.py e as decisões dos bots em bots.py; aqui é só desenho, animação e clique.
"""

import math
from dataclasses import dataclass
from pathlib import Path

# pyrefly: ignore [missing-import]
import pygame

import bots
from regras import CORINGA, EVENTOS, VALORES, Carta, Jogo

VOLUME_DA_MUSICA = 0.4  # de 0 a 1
ESPERA_DO_BOT = 400     # milissegundos de pausa entre as jogadas dos bots
TEMPO_DO_AVISO = 3000   # milissegundos que a explicação do evento fica na tela
TEMPO_CHEGADA = 900     # carta do evento caindo e virando
TEMPO_IDA, TEMPO_AGARRAR, TEMPO_VOLTA = 300, 120, 300  # luva indo, fechando e voltando com a carta

LARGURA, ALTURA = 1280, 720
IMAGENS = Path(__file__).parent / "imagens"
SONS = Path(__file__).parent / "sons"
NOMES = ["Você", "Bot 1", "Bot 2", "Bot 3"]

# Centro da mão de cada jogador. A ordem 0, 1, 2, 3 anda no sentido horário na tela,
# por isso o sentido +1 das regras aparece como "horário".
LUGARES = {
    3: [(640, 600), (330, 150), (950, 150)],
    4: [(640, 600), (190, 360), (640, 120), (1090, 360)],
}
CARTA_GRANDE = (90, 126)   # suas cartas
CARTA_PEQUENA = (70, 98)   # cartas dos bots
CARTA_EVENTO = (150, 210)

MESA = (24, 100, 64)
MESA_CENTRO = (18, 84, 53)
BRANCO = (248, 248, 242)
PRETO = (30, 30, 30)
CINZA = (140, 140, 140)
VERMELHO = (200, 35, 45)
ROXO = (115, 55, 175)
AMARELO = (250, 205, 60)
AZUL_CLARO = (110, 190, 255)
VERSO = (45, 75, 165)


@dataclass
class Pegada:
    """Luva no meio do caminho. A jogada só vale nas regras quando a animação termina."""
    inicio: int
    quem: int
    alvo: int
    indice: int
    carta: Carta


def suavizar(t):
    """Começa rápido e freia no final."""
    return 1 - (1 - t) ** 3


def entre(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def ordem_na_mao(carta):
    return (len(VALORES), "") if carta.coringa else (VALORES.index(carta.valor), carta.naipe)


def pontas_da_estrela(centro, raio):
    cx, cy = centro
    pontos = []
    for i in range(10):
        r = raio if i % 2 == 0 else raio * 0.45
        angulo = math.pi / 2 + i * math.pi / 5
        pontos.append((cx + r * math.cos(angulo), cy - r * math.sin(angulo)))
    return pontos


def quebrar_linha(texto, fonte, largura):
    linhas, atual = [], ""
    for palavra in texto.split():
        tentativa = f"{atual} {palavra}".strip()
        if atual and fonte.size(tentativa)[0] > largura:
            linhas.append(atual)
            atual = palavra
        else:
            atual = tentativa
    return linhas + [atual]


class Tela:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("Jogo de Cartas (protótipo)")
        self.relogio = pygame.time.Clock()
        fonte = "segoeui,arial"  # as duas têm os naipes
        self.f_canto = pygame.font.SysFont(fonte, 18, bold=True)
        self.f_valor = pygame.font.SysFont(fonte, 44, bold=True)
        self.f_valor_pequeno = pygame.font.SysFont(fonte, 32, bold=True)
        self.f_texto = pygame.font.SysFont(fonte, 20)
        self.f_pequeno = pygame.font.SysFont(fonte, 15)
        self.f_titulo = pygame.font.SysFont(fonte, 30, bold=True)
        self.f_capa = pygame.font.SysFont(fonte, 56, bold=True)
        self.luva_aberta = pygame.image.load(IMAGENS / "luva_aberta.png").convert_alpha()
        self.luva_fechada = pygame.image.load(IMAGENS / "luva_fechada.png").convert_alpha()
        self.verso_evento = self.verso_de_evento()
        self.mudo = False
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(str(SONS / "musica.ogg"))
            pygame.mixer.music.set_volume(VOLUME_DA_MUSICA)
            pygame.mixer.music.play(-1)  # -1 = loop infinito
            self.som_coringa = pygame.mixer.Sound(str(SONS / "coringa.ogg"))
        except pygame.error:
            self.som_coringa = None  # PC sem saída de som: o jogo roda mudo
        self.jogo = None  # sem partida = está no menu

    def novo_jogo(self, jogadores):
        self.jogo = Jogo(NOMES[:jogadores])
        self.selecionada = None  # sua carta escolhida na volta de trocas
        self.pegada = None
        self.tinha_coringa = CORINGA in self.jogo.maos[0]
        self.eventos_vistos = 0
        self.face_evento = None
        self.chegada_ate = 0
        self.aviso_ate = 0
        self.bot_pode_jogar = pygame.time.get_ticks() + ESPERA_DO_BOT

    # ---------- laço principal ----------

    def rodar(self):
        while True:
            agora = pygame.time.get_ticks()
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if e.type == pygame.KEYDOWN and e.key == pygame.K_m:
                    self.alternar_som()
                elif self.jogo is None:
                    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        escolha = self.escolha_do_menu(e.pos)
                        if escolha == "sair":
                            return
                        if escolha:
                            self.novo_jogo(escolha)
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                    self.jogo = None
                elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.clicar(e.pos, agora)
            if self.jogo is None:
                self.desenhar_menu()
            else:
                self.atualizar(agora)
                self.desenhar(agora)
            pygame.display.flip()
            self.relogio.tick(60)

    def atualizar(self, agora):
        p = self.pegada
        if p and agora >= p.inicio + TEMPO_IDA + TEMPO_AGARRAR + TEMPO_VOLTA:
            self.pegada = None
            self.jogo.pegar(p.indice)
            self.bot_pode_jogar = agora + ESPERA_DO_BOT
        if self.jogo.eventos_disparados != self.eventos_vistos:
            self.eventos_vistos = self.jogo.eventos_disparados
            self.face_evento = self.carta_de_evento(self.jogo.ultimo_evento)
            self.chegada_ate = agora + TEMPO_CHEGADA
            self.aviso_ate = self.chegada_ate + TEMPO_DO_AVISO
        self.jogar_bots(agora)
        if self.jogo.pedido != ("trocar", 0):
            self.selecionada = None
        # o coringa chegou na sua mão, não importa como: pegando, trocando ou por evento
        tem_coringa = CORINGA in self.jogo.maos[0]
        if tem_coringa and not self.tinha_coringa and self.som_coringa and not self.mudo:
            self.som_coringa.play()
        self.tinha_coringa = tem_coringa

    def alternar_som(self):
        if self.som_coringa is None:
            return
        self.mudo = not self.mudo
        if self.mudo:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.unpause()

    def jogar_bots(self, agora):
        if self.pegada or agora < max(self.bot_pode_jogar, self.aviso_ate):
            return
        tipo, quem = self.jogo.pedido
        if tipo == "passar":
            pendentes = [j for j in quem if j != 0]
            if not pendentes:
                return
            for j in pendentes:
                self.jogo.passar(j, bots.carta_para_dar(self.jogo, j))
            self.bot_pode_jogar = agora + ESPERA_DO_BOT
        elif tipo == "pegar" and quem != 0:
            self.comecar_pegada(bots.posicao_para_pegar(self.jogo, quem), agora)
        elif tipo == "trocar" and quem != 0:
            bots.jogar(self.jogo, quem)
            self.bot_pode_jogar = agora + ESPERA_DO_BOT

    def comecar_pegada(self, indice, agora):
        jogo = self.jogo
        alvo = jogo.de_quem_pega()
        self.pegada = Pegada(agora, jogo.vez, alvo, indice, jogo.maos[alvo][indice])

    def clicar(self, pos, agora):
        if self.pegada:
            return
        if agora < self.chegada_ate:
            self.chegada_ate = agora  # pula a animação e já mostra a explicação
            return
        if agora < self.aviso_ate:
            self.aviso_ate = agora  # clique fecha a explicação do evento
            return
        if self.jogo.vencedor is not None:
            self.novo_jogo(self.jogo.n)
            return
        for r, acao, dado in self.clicaveis():
            if not r.collidepoint(pos):
                continue
            if acao == "selecionar":
                self.selecionada = None if dado == self.selecionada else dado
                return
            if acao == "pegar":
                self.comecar_pegada(dado, agora)
                return
            if acao == "trocar":
                self.jogo.trocar(dado, self.selecionada)
                self.selecionada = None
            elif acao == "passar":
                self.jogo.passar(0, dado)
            self.bot_pode_jogar = agora + ESPERA_DO_BOT
            return

    # ---------- menu ----------

    def botoes_do_menu(self):
        """(retângulo, texto, escolha). Escolha None = botão desligado."""
        opcoes = [
            ("Contra 3 bots", 4),
            ("Contra 2 bots", 3),
            ("Jogar em rede (em breve)", None),
            ("Sair", "sair"),
        ]
        botoes = []
        for i, (texto, escolha) in enumerate(opcoes):
            r = pygame.Rect(0, 0, 380, 56)
            r.center = (640, 320 + i * 76)
            botoes.append((r, texto, escolha))
        return botoes

    def escolha_do_menu(self, pos):
        for r, _, escolha in self.botoes_do_menu():
            if r.collidepoint(pos):
                return escolha
        return None

    def desenhar_menu(self):
        self.tela.fill(MESA)
        self.texto("Jogo de Cartas", self.f_capa, BRANCO, (640, 170))
        self.texto("Feche a quadra e fuja do coringa.", self.f_texto, BRANCO, (640, 230))
        mouse = pygame.mouse.get_pos()
        for r, texto, escolha in self.botoes_do_menu():
            if escolha is None:
                pygame.draw.rect(self.tela, MESA_CENTRO, r, border_radius=12)
                pygame.draw.rect(self.tela, CINZA, r, 2, border_radius=12)
                self.texto(texto, self.f_texto, CINZA, r.center)
            else:
                pygame.draw.rect(self.tela, AMARELO if r.collidepoint(mouse) else BRANCO, r, border_radius=12)
                self.texto(texto, self.f_texto, PRETO, r.center)
        self.texto("M liga e desliga o som", self.f_pequeno, BRANCO, (640, ALTURA - 30))

    # ---------- posições ----------

    def retangulos(self, jogador):
        qtd = len(self.jogo.maos[jogador])
        cx, cy = LUGARES[self.jogo.n][jogador]
        largura, altura = CARTA_GRANDE if jogador == 0 else CARTA_PEQUENA
        passo = largura + 12 if jogador == 0 else 36  # as cartas dos bots ficam sobrepostas
        x = cx - (largura + passo * (qtd - 1)) // 2
        return [pygame.Rect(x + i * passo, cy - altura // 2, largura, altura) for i in range(qtd)]

    def minhas_cartas(self):
        """Sua mão em ordem. As regras embaralham as mãos; aqui só arrumamos para mostrar."""
        mao = sorted(self.jogo.maos[0], key=ordem_na_mao)
        return [(r.move(0, -20) if c == self.selecionada else r, c)
                for r, c in zip(self.retangulos(0), mao)]

    def retangulo_da_carta(self, jogador, carta):
        pares = self.minhas_cartas() if jogador == 0 else zip(self.retangulos(jogador), self.jogo.maos[jogador])
        return next(r for r, c in pares if c == carta)

    def ponto_de_partida(self, jogador):
        """De onde a luva sai: a sua vem de baixo da tela, a dos bots sai da mão deles."""
        return (640, ALTURA + 50) if jogador == 0 else LUGARES[self.jogo.n][jogador]

    def clicaveis(self):
        """Onde dá para clicar agora, do que está por cima para o que está por baixo."""
        if self.pegada:
            return []
        tipo, quem = self.jogo.pedido
        alvos = []
        if tipo == "pegar" and quem == 0:
            alvos = [(r, "pegar", i) for i, r in enumerate(self.retangulos(self.jogo.de_quem_pega()))]
        elif tipo == "trocar" and quem == 0:
            alvos = [(r, "selecionar", c) for r, c in self.minhas_cartas() if not c.coringa]
            if self.selecionada is not None:
                for j in range(1, self.jogo.n):
                    alvos += [(r, "trocar", j) for r in self.retangulos(j)]
        elif tipo == "passar" and 0 in quem:
            alvos = [(r, "passar", c) for r, c in self.minhas_cartas() if not c.coringa]
        return alvos[::-1]

    # ---------- desenho ----------

    def desenhar(self, agora):
        jogo, tela = self.jogo, self.tela
        tela.fill(MESA)
        pygame.draw.ellipse(tela, MESA_CENTRO, (330, 185, 620, 280))

        # a carta que a luva já agarrou sai da mão de onde estava
        p = self.pegada
        na_luva = p.carta if p and agora - p.inicio >= TEMPO_IDA else None

        aberta = jogo.efeito == "maos_abertas" or jogo.vencedor is not None
        for j in range(1, jogo.n):
            for r, c in zip(self.retangulos(j), jogo.maos[j]):
                if c != na_luva:
                    self.carta(r, c, aberta, pequena=True)
            self.nome(j)
        for r, c in self.minhas_cartas():
            if c == na_luva:
                continue
            self.carta(r, c, aberta=True)
            if c == jogo.ultima_recebida[0]:
                pygame.draw.rect(tela, AZUL_CLARO, r.inflate(6, 6), 3, border_radius=10)

        avisando = agora < self.aviso_ate
        if not avisando:
            mouse = pygame.mouse.get_pos()
            em_cima = next((r for r, _, _ in self.clicaveis() if r.collidepoint(mouse)), None)
            if em_cima is not None:
                pygame.draw.rect(tela, AMARELO, em_cima.inflate(6, 6), 3, border_radius=10)

        volta = jogo.turno // jogo.n + 1
        self.texto(f"Volta {volta}   ·   Sentido {jogo.nome_do_sentido()}", self.f_texto, BRANCO, (640, 215))
        if jogo.efeito:
            self.texto(f"Efeito ativo: {EVENTOS[jogo.efeito][0]}", self.f_texto, AMARELO, (640, 243))
        self.texto(self.status(), self.f_texto, BRANCO, (640, 495))
        for i, linha in enumerate(jogo.mensagens(0)):
            self.texto(linha, self.f_pequeno, BRANCO, (15, ALTURA - 150 + i * 19), "topleft")
        self.texto("Objetivo: ficar só com 4 cartas iguais na mão.   Esc: menu   M: som", self.f_pequeno, BRANCO,
                   (LARGURA - 15, ALTURA - 15), "bottomright")

        if p:
            self.desenhar_pegada(agora)
        if agora < self.chegada_ate:
            self.desenhar_chegada(agora)
        elif avisando:
            titulo, descricao = EVENTOS[jogo.ultimo_evento]
            self.caixa(titulo, [descricao] + jogo.resumo_do_evento(0), "clique pra fechar")
        elif jogo.vencedor is not None:
            nome = "Você venceu!" if jogo.vencedor == 0 else f"{jogo.nomes[jogo.vencedor]} venceu!"
            self.caixa(nome, ["Ficou só com as 4 iguais na mão."], "clique pra jogar de novo · Esc volta ao menu")

    def desenhar_pegada(self, agora):
        """A luva vai aberta até a carta, fecha e volta trazendo a carta."""
        p = self.pegada
        t = agora - p.inicio
        casa = self.ponto_de_partida(p.quem)
        alvo = self.retangulo_da_carta(p.alvo, p.carta).center
        if t < TEMPO_IDA:
            pos = entre(casa, alvo, suavizar(t / TEMPO_IDA))
            luva = self.luva_aberta
        else:
            volta = min(1, max(0, t - TEMPO_IDA - TEMPO_AGARRAR) / TEMPO_VOLTA)
            pos = entre(alvo, casa, suavizar(volta))
            luva = self.luva_fechada
            # você vê a sua carta indo embora; a dos outros só aparece em "mãos abertas"
            visivel = p.alvo == 0 or self.jogo.efeito == "maos_abertas"
            r = pygame.Rect((0, 0), CARTA_GRANDE if p.alvo == 0 else CARTA_PEQUENA)
            r.center = pos
            self.carta(r, p.carta, visivel, pequena=p.alvo != 0)
        self.tela.blit(luva, luva.get_rect(center=(pos[0], pos[1] + 12)))

    def desenhar_chegada(self, agora):
        """A carta do evento cai do topo até o meio da mesa e vira."""
        t = 1 - (self.chegada_ate - agora) / TEMPO_CHEGADA
        largura, altura = CARTA_EVENTO
        if t < 0.6:
            imagem = self.verso_evento
            y = -altura + (350 + altura) * suavizar(t / 0.6)
        else:
            k = (t - 0.6) / 0.4  # na metade a carta fica de lado e troca de face
            imagem = self.verso_evento if k < 0.5 else self.face_evento
            imagem = pygame.transform.smoothscale(imagem, (max(1, int(largura * abs(1 - 2 * k))), altura))
            y = 350
        self.tela.blit(imagem, imagem.get_rect(center=(640, y)))

    def verso_de_evento(self):
        imagem = pygame.Surface(CARTA_EVENTO, pygame.SRCALPHA)
        r = imagem.get_rect()
        pygame.draw.rect(imagem, ROXO, r, border_radius=12)
        pygame.draw.rect(imagem, BRANCO, r.inflate(-16, -16), 3, border_radius=8)
        interrogacao = self.f_capa.render("?", True, BRANCO)
        imagem.blit(interrogacao, interrogacao.get_rect(center=r.center))
        return imagem

    def carta_de_evento(self, nome):
        imagem = pygame.Surface(CARTA_EVENTO, pygame.SRCALPHA)
        r = imagem.get_rect()
        pygame.draw.rect(imagem, BRANCO, r, border_radius=12)
        pygame.draw.rect(imagem, ROXO, r, 5, border_radius=12)
        pygame.draw.polygon(imagem, ROXO, pontas_da_estrela((r.centerx, 62), 34))
        for i, linha in enumerate(quebrar_linha(EVENTOS[nome][0], self.f_canto, r.w - 24)):
            texto = self.f_canto.render(linha, True, ROXO)
            imagem.blit(texto, texto.get_rect(center=(r.centerx, 130 + i * 24)))
        return imagem

    def status(self):
        jogo = self.jogo
        tipo, quem = jogo.pedido
        if tipo == "fim":
            return "Clique pra jogar de novo ou aperte Esc pra voltar ao menu."
        if tipo == "passar":
            if 0 in quem:
                return f"Passa uma: escolha a carta que vai pro {jogo.nomes[jogo.proximo(0)]}."
            return "Esperando os outros escolherem..."
        if quem != 0:
            return f"Vez do {jogo.nomes[quem]}..."
        if tipo == "pegar":
            alvo = jogo.nomes[jogo.de_quem_pega()]
            if jogo.efeito == "maos_abertas":
                return f"Sua vez: escolha, vendo, uma carta do {alvo}."
            return f"Sua vez: clique numa carta do {alvo}."
        if self.selecionada is None:
            return "Troca: escolha uma carta sua (menos o coringa)."
        return f"Agora clique na mão de quem vai receber o {self.selecionada}."

    def carta(self, r, carta, aberta, pequena=False):
        tela = self.tela
        if not aberta:
            pygame.draw.rect(tela, VERSO, r, border_radius=8)
            pygame.draw.rect(tela, BRANCO, r.inflate(-12, -12), 2, border_radius=6)
            return
        pygame.draw.rect(tela, BRANCO, r, border_radius=8)
        pygame.draw.rect(tela, CINZA, r, 1, border_radius=8)
        if carta.coringa:
            self.texto("C", self.f_canto, ROXO, (r.x + 7, r.y + 4), "topleft")
            pygame.draw.polygon(tela, ROXO, pontas_da_estrela(r.center, r.w * 0.3))
            return
        cor = VERMELHO if carta.naipe in "♥♦" else PRETO
        self.texto(f"{carta.valor}{carta.naipe}", self.f_canto, cor, (r.x + 7, r.y + 4), "topleft")
        self.texto(carta.valor, self.f_valor_pequeno if pequena else self.f_valor, cor, r.center)

    def nome(self, j):
        jogo = self.jogo
        tipo, quem = jogo.pedido
        da_vez = (tipo in ("pegar", "trocar") and quem == j) or (tipo == "passar" and j in quem)
        topo = self.retangulos(j)[0].top
        texto = f"{jogo.nomes[j]} · {len(jogo.maos[j])} cartas"
        self.texto(texto, self.f_texto, AMARELO if da_vez else BRANCO, (LUGARES[jogo.n][j][0], topo - 16))

    def caixa(self, titulo, linhas, rodape):
        largura = 620
        corpo = [parte for linha in linhas for parte in quebrar_linha(linha, self.f_texto, largura - 40)]
        r = pygame.Rect(0, 0, largura, 110 + 26 * len(corpo))
        r.center = (640, 350)
        pygame.draw.rect(self.tela, BRANCO, r, border_radius=14)
        pygame.draw.rect(self.tela, ROXO, r, 4, border_radius=14)
        self.texto(titulo, self.f_titulo, ROXO, (r.centerx, r.y + 34))
        for i, linha in enumerate(corpo):
            self.texto(linha, self.f_texto, PRETO, (r.centerx, r.y + 72 + i * 26))
        self.texto(rodape, self.f_pequeno, CINZA, (r.centerx, r.bottom - 20))

    def texto(self, texto, fonte, cor, pos, ancora="center"):
        imagem = fonte.render(texto, True, cor)
        self.tela.blit(imagem, imagem.get_rect(**{ancora: pos}))


if __name__ == "__main__":
    Tela().rodar()
    pygame.quit()
