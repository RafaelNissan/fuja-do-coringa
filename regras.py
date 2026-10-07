"""Regras do jogo, sem nada de tela.

A tela (main.py) e os bots (bots.py) só usam a parte pública do Jogo:
pedido, de_quem_pega, proximo, pegar, trocar, passar, mensagens e resumo_do_evento.
Quando vier o modo em rede, o jogador remoto entra pelo mesmo caminho.
"""

import random
from collections import Counter
from dataclasses import dataclass

VALORES = ["A", "K", "Q", "J"]  # uma quadra por jogador: com 3 jogadores usa só A, K e Q
NAIPES = ["♠", "♥", "♦", "♣"]

# Em voltas (uma volta = cada jogador jogou uma vez). Ajuste aqui para calibrar.
PRIMEIRO_EVENTO = (3, 4)    # o primeiro evento sai durante a 3ª ou a 4ª volta
INTERVALO_EVENTOS = (2, 3)  # os seguintes saem 2 a 3 voltas depois do anterior

EVENTOS = {
    "inverter": ("Inverter sentido", "A rodada passa a girar pro outro lado."),
    "girar": ("Girar as mãos", "Todo mundo passa a mão inteira pro vizinho."),
    "coringa_foge": ("Coringa foge", "O coringa troca de lugar com uma carta de alguém sorteado."),
    "maos_abertas": ("Mãos abertas", "Por uma volta, todo mundo pega cartas vendo."),
    "passa_uma": ("Passa uma", "Todos escolhem uma carta e passam pro vizinho."),
    "danca": ("Dança das cadeiras", "As mãos são trocadas aleatoriamente entre os jogadores."),
    "troca": ("Troca com qualquer um", "Por uma volta, cada um troca uma carta às cegas com quem quiser."),
    "revelado": ("Coringa revelado", "Todo mundo fica sabendo quem está com o coringa."),
    "imposto": ("Imposto", "Quem tem 3 iguais troca uma delas com o vizinho."),
    "grudado": ("Coringa grudado", "Por uma volta, ninguém consegue pegar o coringa."),
}


@dataclass(frozen=True)
class Carta:
    valor: str
    naipe: str = ""

    @property
    def coringa(self):
        return self.valor == "CORINGA"

    def __str__(self):
        return "o coringa" if self.coringa else f"{self.valor}{self.naipe}"


CORINGA = Carta("CORINGA")


def tem_quadra(mao):
    """Ganha quem fica só com as 4 iguais na mão: sem coringa e sem carta sobrando."""
    return len(mao) == 4 and len({c.valor for c in mao}) == 1


class Jogo:
    def __init__(self, nomes, rng=None):
        if not 3 <= len(nomes) <= 4:
            raise ValueError("O jogo é para 3 ou 4 jogadores.")
        self.nomes = list(nomes)
        self.n = len(self.nomes)
        self.rng = rng or random.Random()
        self.turno = 0            # jogadas feitas (pegar ou trocar)
        self.vencedor = None
        self.efeito = None        # efeito que dura uma volta: maos_abertas, troca ou grudado
        self.efeito_ate = 0
        self.passes = None        # escolhas do evento "passa uma" enquanto ele espera todo mundo
        self.ultimo_evento = None
        self.eventos_disparados = 0
        self.ultima_recebida = [None] * self.n
        self._log = []
        self._trecho_do_evento = (0, 0)
        self._saco_de_eventos = []
        self._distribuir()
        inicio, fim = PRIMEIRO_EVENTO
        self.proximo_evento = self.rng.randint((inicio - 1) * self.n, fim * self.n - 1)

    # ---------- consultas ----------

    @property
    def pedido(self):
        """O que o jogo espera agora.

        ("pegar", jogador) ou ("trocar", jogador): a vez é desse jogador.
        ("passar", [jogadores]): evento "passa uma" esperando a escolha deles.
        ("fim", vencedor): acabou.
        """
        if self.vencedor is not None:
            return ("fim", self.vencedor)
        if self.passes is not None:
            return ("passar", [j for j in range(self.n) if j not in self.passes])
        return ("trocar" if self.efeito == "troca" else "pegar", self.vez)

    def de_quem_pega(self):
        return (self.vez - self.sentido) % self.n

    def proximo(self, jogador):
        return (jogador + self.sentido) % self.n

    def dono_do_coringa(self):
        return next(j for j, mao in enumerate(self.maos) if CORINGA in mao)

    def nome_do_sentido(self):
        return "horário" if self.sentido == 1 else "anti-horário"

    def mensagens(self, jogador, ultimas=7):
        """Últimas mensagens do ponto de vista de um jogador (cada um só vê as próprias cartas)."""
        return [privado.get(jogador, texto) for texto, privado in self._log[-ultimas:]]

    def resumo_do_evento(self, jogador):
        """O que o último evento causou, do ponto de vista de um jogador."""
        inicio, fim = self._trecho_do_evento
        return [privado.get(jogador, texto) for texto, privado in self._log[inicio:fim]]

    # ---------- jogadas ----------

    def pegar(self, indice):
        """O jogador da vez pega, às cegas, a carta nesta posição da mão de quem tem 5."""
        self._exigir("pegar")
        quem, alvo = self.vez, self.de_quem_pega()
        if not 0 <= indice < len(self.maos[alvo]):
            raise ValueError("Essa carta não existe.")
        carta = self.maos[alvo][indice]
        aviso = ""
        if carta.coringa and self.efeito == "grudado":
            carta = self.rng.choice([c for c in self.maos[alvo] if not c.coringa])
            aviso = "O coringa está grudado! "
        self._mover(carta, alvo, quem)
        self._registrar(f"{self.nomes[quem]} pegou uma carta de {self.nomes[alvo]}.", {
            quem: f"{aviso}Você pegou {carta} de {self.nomes[alvo]}.",
            alvo: f"{self.nomes[quem]} pegou {carta} da sua mão.",
        })
        self._fim_da_jogada()

    def trocar(self, alvo, carta):
        """Durante "Troca com qualquer um": dá uma carta sua e recebe uma às cegas de quem escolheu."""
        self._exigir("trocar")
        quem = self.vez
        if alvo == quem or not 0 <= alvo < self.n:
            raise ValueError("Escolha outro jogador para trocar.")
        self._exigir_carta_para_dar(quem, carta)
        recebida = self.rng.choice(self.maos[alvo])
        self._mover(carta, quem, alvo)
        self._mover(recebida, alvo, quem)
        self._registrar(f"{self.nomes[quem]} trocou uma carta com {self.nomes[alvo]}.", {
            quem: f"Você deu {carta} pra {self.nomes[alvo]} e recebeu {recebida}.",
            alvo: f"{self.nomes[quem]} te deu {carta} e levou {recebida}.",
        })
        self._fim_da_jogada()

    def passar(self, jogador, carta):
        """Evento "passa uma": cada um escolhe; quando todos escolheram, passam juntos pro vizinho."""
        self._exigir("passar")
        if not 0 <= jogador < self.n or jogador in self.passes:
            raise ValueError("Esse jogador não precisa escolher.")
        self._exigir_carta_para_dar(jogador, carta)
        self.passes[jogador] = carta
        if len(self.passes) < self.n:
            return
        privado = {}
        for j, c in self.passes.items():
            self._mover(c, j, self.proximo(j))
            recebida = self.passes[(j - self.sentido) % self.n]
            privado[j] = f"Você passou {c} e recebeu {recebida}."
        self.passes = None
        self._registrar("Todo mundo passou uma carta pro vizinho.", privado)
        self._checar_vencedor()

    # ---------- andamento ----------

    def _fim_da_jogada(self):
        self.turno += 1
        if self._checar_vencedor():
            return
        if self.efeito and self.turno >= self.efeito_ate:
            self._registrar(f"Acabou o efeito {EVENTOS[self.efeito][0]}.")
            self.efeito = None
        if self.efeito == "troca":
            self.vez = self.proximo(self.vez)  # na volta de trocas ninguém muda de tamanho de mão
        else:
            self.vez = self._depois_de_quem_tem_5()
        if self.turno >= self.proximo_evento:
            self._disparar_evento()

    def _depois_de_quem_tem_5(self):
        """Regra de ordem: joga sempre quem está logo depois de quem tem 5 cartas."""
        dono = max(range(self.n), key=lambda j: len(self.maos[j]))
        return self.proximo(dono)

    def _checar_vencedor(self):
        for k in range(self.n):
            j = (self.vez + k * self.sentido) % self.n
            if tem_quadra(self.maos[j]):
                self.vencedor = j
                self._registrar(f"{self.nomes[j]} fechou a quadra e venceu!")
                return True
        return False

    def _disparar_evento(self, nome=None):
        if nome is None:
            if not self._saco_de_eventos:  # sorteia sem repetir até saírem todos
                self._saco_de_eventos = list(EVENTOS)
                self.rng.shuffle(self._saco_de_eventos)
            nome = self._saco_de_eventos.pop()
        self.ultimo_evento = nome
        self.eventos_disparados += 1
        self._registrar(f"Evento: {EVENTOS[nome][0]}!")
        inicio = len(self._log)
        getattr(self, f"_evento_{nome}")()
        self._trecho_do_evento = (inicio, len(self._log))
        minimo, maximo = INTERVALO_EVENTOS
        self.proximo_evento = self.turno + self.rng.randint(minimo * self.n, maximo * self.n)
        self.vez = self._depois_de_quem_tem_5()
        if self.passes is None:
            self._checar_vencedor()

    # ---------- os 10 eventos ----------
    # Todo evento que mexe em carta é troca 1 por 1: ninguém pode ficar com menos de 4.

    def _evento_inverter(self):
        self.sentido = -self.sentido
        self._registrar(f"Agora o sentido é {self.nome_do_sentido()}.")

    def _evento_girar(self):
        self.maos = [self.maos[(j - self.sentido) % self.n] for j in range(self.n)]
        self.ultima_recebida = [None] * self.n

    def _evento_coringa_foge(self):
        dono = self.dono_do_coringa()
        outro = self.rng.choice([j for j in range(self.n) if j != dono])
        carta = self.rng.choice(self.maos[outro])
        self._mover(CORINGA, dono, outro)
        self._mover(carta, outro, dono)
        self._registrar("O coringa fugiu pra outra mão!", {
            dono: f"O coringa saiu da sua mão e no lugar veio {carta}.",
            outro: f"O coringa veio pra sua mão e levou {carta}.",
        })

    def _evento_maos_abertas(self):
        self._comecar_efeito("maos_abertas")

    def _evento_passa_uma(self):
        self.passes = {}

    def _evento_danca(self):
        ordem = list(range(self.n))
        while any(i == o for i, o in enumerate(ordem)):  # ninguém fica com a própria mão
            self.rng.shuffle(ordem)
        self.maos = [self.maos[o] for o in ordem]
        self.ultima_recebida = [None] * self.n

    def _evento_troca(self):
        self._comecar_efeito("troca")

    def _evento_revelado(self):
        dono = self.dono_do_coringa()
        self._registrar(f"{self.nomes[dono]} está com o coringa!",
                        {dono: "Todo mundo sabe que você está com o coringa!"})

    def _evento_imposto(self):
        pagou = False
        for j in range(self.n):
            valor, qtd = Counter(c.valor for c in self.maos[j] if not c.coringa).most_common(1)[0]
            if qtd < 3:
                continue
            vizinho = self.proximo(j)
            dada = self.rng.choice([c for c in self.maos[j] if c.valor == valor])
            recebida = self.rng.choice(self.maos[vizinho])
            self._mover(dada, j, vizinho)
            self._mover(recebida, vizinho, j)
            self._registrar(f"{self.nomes[j]} pagou imposto: deu {dada} pra {self.nomes[vizinho]}.", {
                j: f"Você pagou imposto: deu {dada} e recebeu {recebida}.",
                vizinho: f"{self.nomes[j]} pagou imposto: te deu {dada} e levou {recebida}.",
            })
            pagou = True
        if not pagou:
            self._registrar("Ninguém tinha 3 iguais, ninguém pagou.")

    def _evento_grudado(self):
        self._comecar_efeito("grudado")

    def _comecar_efeito(self, nome):
        self.efeito = nome
        self.efeito_ate = self.turno + self.n

    # ---------- apoio ----------

    def _distribuir(self):
        baralho = [Carta(v, s) for v in VALORES[:self.n] for s in NAIPES]
        while True:
            self.rng.shuffle(baralho)
            self.maos = [baralho[i * 4:(i + 1) * 4] for i in range(self.n)]
            if not any(tem_quadra(m) for m in self.maos):  # ninguém começa já ganhando
                break
        dono = self.rng.randrange(self.n)
        self.maos[dono].append(CORINGA)
        self.rng.shuffle(self.maos[dono])
        self.sentido = self.rng.choice((1, -1))
        self.vez = self._depois_de_quem_tem_5()
        self._registrar(f"Nova partida. Sentido {self.nome_do_sentido()}. {self.nomes[self.vez]} começa.")

    def _mover(self, carta, de, para):
        self.maos[de].remove(carta)
        self.maos[para].append(carta)
        self.ultima_recebida[para] = carta
        # embaralha para a posição da carta não entregar nada a quem pega às cegas
        self.rng.shuffle(self.maos[de])
        self.rng.shuffle(self.maos[para])

    def _exigir(self, tipo):
        if self.pedido[0] != tipo:
            raise RuntimeError(f"Agora não é hora de {tipo}.")

    def _exigir_carta_para_dar(self, jogador, carta):
        if carta.coringa or carta not in self.maos[jogador]:
            raise ValueError("Escolha uma carta sua que não seja o coringa.")

    def _registrar(self, texto, privado=None):
        self._log.append((texto, privado or {}))
