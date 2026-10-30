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
pythonw clawd.pyw        # sem janela de terminal (ou duplo clique no clawd.pyw)
```

Pra fechar: clique direito → **Sair** (ou Ctrl+C no terminal). Só abre um Clawd por vez.

## Interação

| Ação | O que acontece |
|---|---|
| Clique esquerdo | Carinho: coração sobe e a felicidade aumenta. Se estiver dormindo, acorda |
| Clique direito | Menu: Alimentar, Brincar, Dormir, Status, Clima, Sair |
| Arrastar (≥ 5 px) | Fica pendurado balançando as perninhas; ao soltar cai com gravidade |
| Arrastar e soltar rápido | Sai voando nessa direção e quica nas bordas |
| Chacoalhar | Fica tonto por 4 s, com estrelinhas, e perde felicidade |
| Clique no balão | Fecha o balão |

Ele volta pro lugar onde foi solto por último quando o programa abre.

## Sprites

Enquanto não houver PNGs, o Clawd é desenhado em pixel direto no código (`clawd/pixelart.py`).
Pra trocar, crie uma pasta por animação com os quadros em PNG de fundo transparente, virados pra direita:

```
sprites/
  parado/      01.png 02.png ...
  andando/
  dormindo/
  pendurado/
  caindo/
  comendo/
  comemorando/
  acenando/
  escondido/
  tonto/
```

- Os quadros tocam em ordem alfabética. Um `anim.json` opcional define a velocidade: `{"ms": 120}`.
- O tamanho é ajustado sozinho pra ~70 px de altura (com zoom inteiro, sem borrar).
- Use transparência total ou nenhuma (sem semitransparência), senão aparece contorno escuro.
- Animação sem pasta continua usando o desenho provisório.
- Quando vier a evolução, `sprites/<fase>/<animacao>/` tem prioridade sobre `sprites/<animacao>/`.

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
  sprites.py       carrega PNGs ou o desenho provisório
  pixelart.py      o Clawd provisório em pixel
  balao.py         balão de fala
  efeitos.py       coração, Zzz, migalhas, estrelinhas
  tela.py          API do Windows (DPI, área de trabalho, instância única)
tests/             python -m unittest discover -s tests -t .
clawd.json         save (criado ao rodar)
clawd.log          erros e avisos
```
