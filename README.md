# Fuja do Coringa

Jogo de cartas feito em Python com pygame-ce. O objetivo é fechar uma quadra (4 cartas iguais) **sem** estar com o coringa na mão.

Ainda é um protótipo: por enquanto dá pra jogar só contra bots.

## Como funciona

- Mesa com 3 ou 4 jogadores. O baralho tem uma quadra por jogador (com 4 na mesa: A, K, Q e J) e mais 1 coringa.
- Todo mundo começa com 4 cartas. Quem recebe o coringa fica com 5.
- Na sua vez, você pega uma carta às cegas da mão do vizinho.
- Ganha quem juntar 4 cartas iguais sem o coringa na mão.
- Pegou o coringa? Não dá pra jogar ele fora. Você só se livra dele quando alguém pega da sua mão.
- Joga sempre quem está logo depois de quem tem 5 cartas.

## Eventos

Na 3ª ou 4ª volta aparece o primeiro evento no meio da mesa. Ele vale na hora pra todo mundo. Depois disso, sai um novo a cada 2 ou 3 voltas.

| Evento | O que faz |
|---|---|
| Inverter sentido | A rodada passa a girar pro outro lado. |
| Girar as mãos | Todo mundo passa a mão inteira pro vizinho. |
| Coringa foge | O coringa troca de lugar com uma carta de alguém sorteado. |
| Mãos abertas | Por uma volta, todo mundo pega carta vendo. |
| Passa uma | Cada um escolhe uma carta e passa pro vizinho, todos ao mesmo tempo. |
| Dança das cadeiras | As mãos são trocadas aleatoriamente entre os jogadores. |
| Troca com qualquer um | Por uma volta, cada um troca uma carta às cegas com quem quiser. |
| Coringa revelado | Todo mundo fica sabendo quem está com o coringa. |
| Imposto | Quem tem 3 iguais troca uma delas com o vizinho. |
| Coringa grudado | Por uma volta, ninguém consegue pegar o coringa. |

Todo evento que mexe em carta é uma troca 1 por 1. Assim ninguém fica com menos de 4 cartas e todo mundo continua com chance de ganhar.

## Como rodar

Precisa do Python 3.12 ou mais novo. No Windows, dentro da pasta do projeto:

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

## Testes

O `testar_regras.py` simula 2 mil partidas só com bots e confere se alguma regra quebra: carta sumindo, mão desequilibrada, coringa grudado sendo pego, partida que nunca acaba. Não precisa do pygame.

```bash
python testar_regras.py
```

## Estrutura

| Arquivo | O que tem |
|---|---|
| `regras.py` | As regras e os 10 eventos. Aqui não tem nada de tela. |
| `bots.py` | Como os bots decidem as jogadas. |
| `main.py` | Menu, tela e cliques, usando pygame-ce. |
| `testar_regras.py` | Simulação que testa as regras. |

As regras ficam separadas da tela de propósito: quando vier o modo em rede, o jogador remoto entra pelo mesmo caminho que a tela usa hoje.

## Próximos passos

- [ ] Modo em rede: um jogador vira host e os bots completam a mesa
- [ ] Gerar o `.exe` com PyInstaller
- [ ] Publicar no itch.io
