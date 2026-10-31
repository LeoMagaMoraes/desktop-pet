# Clawd 🦀 — mascote de desktop

O caranguejinho do Claude Code morando em cima da barra de tarefas, no estilo tamagotchi.

## O que precisa instalar

- **Python 3.10 ou mais novo** pelo [python.org](https://www.python.org/downloads/windows/), com a opção
  *tcl/tk and IDLE* marcada (já vem marcada por padrão). Sem pacotes extras do `pip` por enquanto.

Pra conferir se o tkinter está ok: `python -c "import tkinter; tkinter._test()"`

## Como rodar

```powershell
cd C:\Users\leozy\OneDrive\Documentos\VSCODE\Tamagochi
python main.py           # normal
python main.py --demo    # passa por todas as animações (não salva nada)
python main.py --demo --fase anciao   # demo de uma fase: ovo, filhote, clawd ou anciao
pythonw clawd.pyw        # sem janela de terminal (ou duplo clique no clawd.pyw)
```

Pra fechar: clique direito → **Sair** (ou Ctrl+C no terminal). Só abre um Clawd por vez.

## Interação

| Ação | O que acontece |
|---|---|
| Clique esquerdo | Carinho: coração sobe, +felicidade e +1 XP. Se estiver dormindo, acorda |
| Clique direito | Menu: Alimentar, Brincar, Dormir/Acordar, Remédio, Status, Clima, Monitor, Modo Tamagotchi, Sair |
| Passar o mouse por cima, esfregando | Banho: tira a sujeira e solta bolhas de sabão |
| Arrastar (≥ 5 px) | Fica pendurado balançando as perninhas; ao soltar cai com gravidade |
| Arrastar e soltar rápido | Sai voando nessa direção e quica nas bordas |
| Chacoalhar | Fica tonto por 4 s, com estrelinhas, e perde felicidade |
| Clique no balão | Fecha o balão |

Ele volta pro lugar onde foi solto por último quando o programa abre.

### Vários monitores

- **Menu → Monitor** lista os monitores ligados (só fica ativo quando tem mais de um). Escolhendo outro,
  ele cai lá do alto no meio da tela nova e passa a andar sobre a barra de tarefas dela.
- Arrastar e soltar ele em cima de outro monitor também muda a "casa" dele.
- O monitor fica salvo no `clawd.json`. Se ele for desligado, o Clawd volta pro principal sozinho.

## Tamagotchi

Fome, energia e felicidade vão de 0 a 100 (100 = ótimo). A sujeira vai de 0 (limpinho) a 100.

| | Acordado | Dormindo | PC desligado |
|---|---|---|---|
| Fome | −6/h | −3/h | −2/h |
| Energia | −7/h | +40/h | +40/h (dorme) |
| Felicidade | −2/h (−6/h se você sumir do PC por 5 min) | igual | −2/h |
| Sujeira | +5/h | +2/h | +1/h |

- **Tempo fora:** ao abrir, ele desconta o tempo desde o último save (até 30 dias) e conta quanto tempo ficou sozinho.
- **Avisos:** balão com 🍖, 💤, 😢, 🪰 ou 🤒 quando algo fica abaixo de 25 (ou sujeira acima de 70), no máximo a cada 10–15 min.
- **Sono:** com energia abaixo de 15 ele cochila sozinho e acorda quando ela chega em 95. Cansado ou gripado, anda mais devagar.
- **Gripe:** 2 horas seguidas com fome abaixo de 20 deixam ele gripado (espirros, mais gasto de energia). Só cura com **Remédio**.
- **Banho:** com sujeira acima de 55 aparecem mosquinhas. Esfregue o mouse em cima dele até ficar "Cheirosinho!".
- **Evolução por XP:** Ovo (0) → Filhote (100) → Clawd (1.000) → Clawd ancião (10.000, de cartola, óculos e barba).
  XP vem de carinho (+1, a cada 3 s), comida (+5), brincadeira (+5), banho completo (+5), remédio (+2) e
  1 XP por minuto com você no PC. O ovo choca mais rápido (1 XP a cada 10 s, uns 17 min) e não sente fome.
- **Status** no menu abre um painel com a fase, o XP até a próxima e as barrinhas.

### Modo Tamagotchi (liga/desliga no menu)

Desligado, ele vira só um mascote: os status ficam **pausados** (nem o tempo com o PC desligado conta),
sem avisos, gripe, sujeira nem mosquinhas. Alimentar e brincar continuam animando e o XP continua subindo,
então ele ainda evolui. Ao religar, ele continua de onde parou.

Os números ficam em `clawd/necessidades.py` (taxas) e `clawd/config.py` (XP e limiares).

## Sprites

Enquanto não houver PNGs, o Clawd é desenhado em pixel direto no código (`clawd/pixelart.py`).
Pra trocar, crie uma pasta por animação com os quadros em PNG de fundo transparente, virados pra direita:

```
sprites/
  parado/      01.png 02.png ...     ← Clawd adulto
  andando/
  dormindo/
  pendurado/
  caindo/
  comendo/
  comemorando/
  acenando/
  escondido/
  tonto/
  espirrando/
  ovo/<animacao>/        ← cada fase pode ter as suas (+ chocando/ no ovo)
  filhote/<animacao>/
  anciao/<animacao>/
```

- Os quadros tocam em ordem alfabética. Um `anim.json` opcional define a velocidade: `{"ms": 120}`.
- O tamanho é ajustado sozinho pra ~70 px de altura (com zoom inteiro, sem borrar).
- Use transparência total ou nenhuma (sem semitransparência), senão aparece contorno escuro.
- Animação sem pasta continua usando o desenho provisório.
- `sprites/<fase>/<animacao>/` vale pra aquela fase. As pastas soltas em `sprites/<animacao>/` são do Clawd
  adulto (fase `clawd`); ovo, filhote e ancião sem PNG usam o desenho provisório deles.

## Arquivos

```
main.py            ponto de entrada
clawd.pyw          abre sem terminal
clawd/
  config.py        constantes (velocidades, gravidade, limiares)
  mascote.py       janela, ações, mouse e loop de animação
  fisica.py        gravidade, arremesso e quiques (sem Tk)
  interacao.py     clique x arrasto, velocidade do arremesso, sacudida (sem Tk)
  estado.py        save em clawd.json
  necessidades.py  regras do tamagotchi: taxas, gripe, tempo offline, fases (sem Tk)
  tamagotchi.py    liga as regras ao mascote: avisos, sono, espirros, banho, XP
  painel.py        janela de Status
  sprites.py       carrega PNGs ou o desenho provisório
  pixelart.py      o Clawd provisório em pixel
  balao.py         balão de fala
  efeitos.py       coração, Zzz, migalhas, bolhas, gotas, estrelinhas, mosquinhas
  tela.py          API do Windows (DPI, área de trabalho, tempo ocioso, instância única)
tests/             python -m unittest discover -s tests -t .
clawd.json         save (criado ao rodar)
clawd.log          erros e avisos
```
