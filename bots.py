"""Como os bots decidem.

Pegar carta normalmente é às cegas, então o bot só pensa quando existe escolha
de verdade: mãos abertas, troca com qualquer um e passa uma.
"""


def utilidade(mao, carta):
    """Quantas cartas iguais a esta já existem na mão. O coringa nunca ajuda."""
    if carta.coringa:
        return -1
    return sum(1 for c in mao if c.valor == carta.valor)


def carta_para_dar(jogo, jogador):
    """A carta que menos ajuda (nunca o coringa, que não pode ser dado)."""
    mao = jogo.maos[jogador]
    opcoes = [c for c in mao if not c.coringa]
    pior = min(utilidade(mao, c) for c in opcoes)
    return jogo.rng.choice([c for c in opcoes if utilidade(mao, c) == pior])


def posicao_para_pegar(jogo, jogador):
    mao_alvo = jogo.maos[jogo.de_quem_pega()]
    if jogo.efeito != "maos_abertas":
        return jogo.rng.randrange(len(mao_alvo))
    minha = jogo.maos[jogador]
    melhor = max(utilidade(minha, c) for c in mao_alvo)
    return jogo.rng.choice([i for i, c in enumerate(mao_alvo) if utilidade(minha, c) == melhor])


def jogar(jogo, jogador):
    """Faz a jogada da vez deste bot (pegar ou trocar)."""
    tipo, quem = jogo.pedido
    if quem != jogador:
        raise RuntimeError("Não é a vez deste bot.")
    if tipo == "pegar":
        jogo.pegar(posicao_para_pegar(jogo, jogador))
    elif tipo == "trocar":
        alvo = jogo.rng.choice([j for j in range(jogo.n) if j != jogador])
        jogo.trocar(alvo, carta_para_dar(jogo, jogador))
