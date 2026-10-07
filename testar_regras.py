"""Simula partidas só com bots e confere se alguma regra quebra.

Rode com: python testar_regras.py
Não precisa do pygame.
"""

import random

import bots
from regras import CORINGA, EVENTOS, Jogo, tem_quadra

PARTIDAS = 1000


def conferir(jogo):
    cartas = [c for mao in jogo.maos for c in mao]
    assert len(cartas) == 4 * jogo.n + 1, "sumiu ou apareceu carta"
    assert len(set(cartas)) == len(cartas), "carta repetida"
    assert cartas.count(CORINGA) == 1, "coringa sumiu ou duplicou"
    tamanhos = sorted(len(m) for m in jogo.maos)
    assert tamanhos == [4] * (jogo.n - 1) + [5], f"mãos desequilibradas: {tamanhos}"
    tipo, _ = jogo.pedido
    if tipo == "pegar":
        assert len(jogo.maos[jogo.de_quem_pega()]) == 5, "a vez não está depois de quem tem 5"
    if tipo != "fim":
        assert not any(tem_quadra(m) for m in jogo.maos), "alguém fechou a quadra e o jogo não acabou"


def jogada(jogo):
    tipo, quem = jogo.pedido
    if tipo == "passar":
        for j in quem:
            jogo.passar(j, bots.carta_para_dar(jogo, j))
        return
    grudado = tipo == "pegar" and jogo.efeito == "grudado"
    dono = jogo.dono_do_coringa()
    bots.jogar(jogo, quem)
    if grudado:
        assert jogo.dono_do_coringa() == dono, "alguém pegou o coringa grudado"


def ate_o_fim(jogo, limite=20000):
    conferir(jogo)
    while jogo.vencedor is None:
        jogada(jogo)
        conferir(jogo)
        assert jogo.turno < limite, "a partida não acaba"
    return jogo


def main():
    for n in (3, 4):
        voltas, eventos = [], []
        for semente in range(PARTIDAS):
            jogo = ate_o_fim(Jogo([f"Bot {i}" for i in range(n)], random.Random(semente)))
            voltas.append(jogo.turno / n)
            eventos.append(jogo.eventos_disparados)
        print(f"{n} jogadores: {PARTIDAS} partidas sem erro. "
              f"Voltas por partida: média {sum(voltas) / PARTIDAS:.1f}, máximo {max(voltas):.0f}. "
              f"Eventos por partida: média {sum(eventos) / PARTIDAS:.1f}.")

    for nome in EVENTOS:
        for semente in range(300):
            rng = random.Random(semente)
            jogo = Jogo([f"Bot {i}" for i in range(4)], rng)
            for _ in range(rng.randrange(2 * jogo.n)):  # antes do primeiro evento natural
                if jogo.vencedor is None:
                    jogada(jogo)
            if jogo.vencedor is None:
                jogo._disparar_evento(nome)
            ate_o_fim(jogo)
    print(f"Cada um dos {len(EVENTOS)} eventos forçado em 300 partidas: sem erro.")


if __name__ == "__main__":
    main()
