<div align="center">

<img src="docs/clawd.gif" width="176" alt="Clawd acenando, andando, comemorando, digitando e dormindo">

# Pet de Desktop

**O Clawd, o caranguejinho do Claude Code, e a turma dele morando na sua barra de tarefas.**

<img src="docs/turma.png" width="560" alt="Clawd, dragãozinho, tubarãozinho, pinguinzinho, patinho de borracha, fênix e corujinha">

Um tamagotchi de desktop que come os seus prompts, comemora quando a task termina,
cai duro quando os testes quebram e acena quando o Claude precisa de você.

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Dependências](https://img.shields.io/badge/depend%C3%AAncias-nenhuma-7BC67B)
![Testes](https://img.shields.io/badge/testes-198%20passando-7BC67B)
![Claude Code](https://img.shields.io/badge/Claude%20Code-hooks-D97757)

[Instalar](#-instalar) · [Usar](#-usar) · [Tamagotchi](#-tamagotchi) · [Pets](#-pets) · [Clima](#-clima) · [Claude Code](#-integração-com-o-claude-code) · [Sprites](#-sprites-próprios) · [Estrutura](#-estrutura)

</div>

<p align="center">
  <img src="docs/claude_code.png" alt="Clawd digitando enquanto o Claude trabalha, acenando quando precisa de você e comemorando o fim da task">
</p>

## ✨ O que ele faz

- 🦀 **Vive na tela:** anda sobre a barra de tarefas, vira nas bordas, e dá pra pegar, arremessar e chacoalhar (ele fica tonto).
- 🍖 **É um tamagotchi:** tem fome, energia, felicidade e sujeira, sente o tempo com o PC desligado, pega gripe e evolui de ovo até Clawd ancião.
- 🤖 **Conversa com o Claude Code:** reage aos seus prompts, ao fim de cada task, a testes passando ou falhando e a comandos com erro.
- 📊 **Conta tokens:** da sessão, da task e dos últimos 7 dias, com meta semanal.
- 🌦️ **Sente o tempo lá fora:** se veste conforme o clima de verdade, faz chover na sua tela, se esconde na
  trovoada e avisa de manhã se vai chover.
- 🐉 **Sete pets:** Clawd, dragãozinho, tubarãozinho, pinguinzinho, patinho de borracha, fênix e corujinha,
  cada um com o próprio progresso e o próprio jeito.
- 🖥️ **Se vira em vários monitores** e lembra onde você o deixou.
- 🪶 **Leve:** Python puro com tkinter, sem nada pra instalar pelo `pip`.

## 🚀 Instalar

1. Instale o **Python 3.10 ou mais novo** pelo [python.org](https://www.python.org/downloads/windows/), deixando
   marcada a opção *tcl/tk and IDLE* (já vem marcada).
2. Baixe o projeto:
   ```powershell
   git clone https://github.com/LeoMagaMoraes/clawd-desktop-pet.git
   cd clawd-desktop-pet
   ```
3. Crie o atalho **Pet** na área de trabalho:
   ```powershell
   python criar_atalho.py                 # use --menu-iniciar pra pôr no Menu Iniciar também
   ```
4. Ligue a integração com o Claude Code (opcional, mas é a parte mais legal):
   ```powershell
   python instalar_hooks.py
   ```

Pronto: dois cliques no atalho **Pet** e ele aparece em cima da barra de tarefas.

<details>
<summary>Outras formas de abrir</summary>

```powershell
python main.py                          # com terminal (mostra erros)
pythonw pet.pyw                         # sem terminal
python main.py --demo                   # passa por todas as animações, sem salvar nada
python main.py --demo --fase anciao     # demo de uma fase: ovo, filhote, clawd ou anciao
python main.py --demo --pet fenix       # demo de outro pet (dragao, tubarao, pinguim, pato, fenix, coruja)
```

Só abre um Clawd por vez. Pra fechar: clique direito → **Sair**.
</details>

## 🖱️ Usar

| Ação | O que acontece |
|---|---|
| **Clique** | Carinho: um coração sobe, ganha felicidade e XP, e ele diz a temperatura lá fora. Se estiver dormindo, acorda |
| **Clique direito** | Abre o menu |
| **Arrastar** | Ele fica pendurado balançando as perninhas e cai com gravidade ao soltar |
| **Arrastar e soltar rápido** | Sai voando e quica nas bordas da tela |
| **Chacoalhar** | Fica tonto, com estrelinhas, e perde um pouco de felicidade |
| **Esfregar o mouse em cima** | Banho: tira a sujeira e solta bolhas de sabão |
| **Soltar em outro monitor** | Passa a morar naquele monitor |

<table>
  <tr>
    <td align="center"><img src="docs/menu.png" width="300" alt="Menu do clique direito"></td>
    <td align="center"><img src="docs/painel.png" width="300" alt="Painel de status e tokens"></td>
  </tr>
  <tr>
    <td align="center"><b>Menu</b><br><sub>barrinhas dos status, chaves liga/desliga e páginas pra Monitor e Claude Code</sub></td>
    <td align="center"><b>Status e tokens</b><br><sub>fase, XP, necessidades e o uso do Claude Code neste PC</sub></td>
  </tr>
</table>

## 🥚 Tamagotchi

<p align="center"><img src="docs/fases.png" alt="Ovo, filhote, Clawd e Clawd ancião"></p>

| Fase | XP | Como é |
|---|---|---|
| Ovo | 0 | Não anda nem come. Faz carinho que ele choca em uns 17 minutos |
| Filhote | 100 | Pequenininho, já come, brinca e reage ao Claude Code |
| Clawd | 1.000 | O caranguejinho de sempre |
| Clawd ancião | 10.000 | De cartola, óculos e barba |

O XP vem de carinho, comida, brincadeira, banho, remédio, testes passando, tasks do Claude Code
e de 1 XP por minuto com você no PC.

**Necessidades** (0 a 100, 100 = ótimo). Quando alguma fica baixa ele avisa com um balão 🍖 💤 😢 🪰 🤒.

| | Acordado | Dormindo | PC desligado |
|---|---|---|---|
| Fome | −6/h | −3/h | −2/h |
| Energia | −7/h | +40/h | recupera (dorme) |
| Felicidade | −2/h (−6/h se você sumir do PC) | igual | −2/h |
| Sujeira | +5/h | +2/h | +1/h |

- **Sono:** com a energia abaixo de 15 ele cochila sozinho e acorda quando ela chega em 95.
- **Gripe:** 2 horas seguidas com fome abaixo de 20 deixam ele espirrando. Só cura com **Dar remédio**.
- **Banho:** com sujeira acima de 55 aparecem mosquinhas. Esfregue o mouse nele até ouvir "Cheirosinho!".
- **Tempo fora:** ao abrir, ele desconta o tempo desde a última vez (até 30 dias) e conta quanto tempo ficou sozinho.

> [!TIP]
> Não quer cuidar de ninguém hoje? Desligue o **Modo Tamagotchi** no menu: os status ficam pausados
> (nem o tempo com o PC desligado conta), sem avisos nem gripe. Ele continua passeando e ganhando XP.

## 🐉 Pets

Menu → **Trocar de pet**. Além do Clawd 🦀, tem mais seis, cada um com o seu jeito:

| Fases | Pet | Como é | Jeito |
|---|---|---|---|
| <img src="docs/dragao_fases.png" width="300" alt="Ovo de dragão, filhote, dragão e dragão ancião"> | **Dragãozinho** 🐉 | Verde, asinhas que batem quando ele levanta os braços, chifres, crista e cauda com espinho | Espirra faísca 🔥 |
| <img src="docs/tubarao_fases.png" width="300" alt="Ovo de tubarão, filhote, tubarão e tubarão ancião"> | **Tubarãozinho** 🦈 | Azul de barriga branca, sorriso de dentinhos, barbatana, cauda em meia-lua e guelras | Nasce de uma cápsula marrom (a "bolsa de sereia", como muitos tubarões de verdade). Espirra bolhas 💦. Escondido na trovoada, só a barbatana fica de fora |
| <img src="docs/pinguim_fases.png" width="300" alt="Ovo de pinguim, filhote, pinguim e pinguim ancião"> | **Pinguinzinho** 🐧 | Preto de rosto e barriga brancos, bico e pezinhos laranja | **Ama frio:** abaixo de 15 °C fica feliz em vez de sentir fome e dispensa o agasalho. Acima de 25 °C cansa mais e já liga o ventilador. Espirra floco de neve ❄ |
| <img src="docs/pato_fases.png" width="300" alt="Ovo de pato, filhote, pato de borracha e pato ancião"> | **Patinho de borracha** 🦆 | Amarelo, bicão laranja e topetinho | O pato do *rubber duck debugging*: quando um comando falha, pergunta **"Já explicou o problema pra mim? Linha por linha"**. Faz quack no carinho |
| <img src="docs/fenix_fases.png" width="300" alt="Ovo de fênix, filhote, fênix e fênix anciã"> | **Fênix** 🔥 | Vermelha com peito dourado, asas, crista e cauda de fogo | **Renasce:** se a felicidade zerar, vira cinzas, volta pro ovo e renasce na hora, sem perder o XP. Espirra faísca |
| <img src="docs/coruja_fases.png" width="300" alt="Ovo de coruja, filhote, coruja e coruja anciã"> | **Corujinha** 🦉 | Marrom, discos claros nos olhos, orelhinhas de pena e peito pintadinho | **Noturna:** de dia cochila de pijama e cansa rápido; de noite fica esperta, alegre e gasta pouca energia. Espirra pena 🪶 |

<details>
<summary>Ver as poses de cada um</summary>
<p align="center">
  <img src="docs/dragao_poses.png" width="420" alt="Dragãozinho em várias poses"><br>
  <img src="docs/tubarao_poses.png" width="420" alt="Tubarãozinho em várias poses"><br>
  <img src="docs/pinguim_poses.png" width="420" alt="Pinguinzinho em várias poses"><br>
  <img src="docs/pato_poses.png" width="420" alt="Patinho de borracha em várias poses"><br>
  <img src="docs/fenix_poses.png" width="420" alt="Fênix em várias poses"><br>
  <img src="docs/coruja_poses.png" width="420" alt="Corujinha em várias poses">
</p>
</details>

- Eles fazem **tudo** que o Clawd faz: necessidades, evolução (ovo → filhote → adulto → ancião de cartola,
  óculos e barba), roupas do clima, reações ao Claude Code, menu, física e tontura.
- **Cada pet tem o próprio progresso.** Da primeira vez o pet novo chega como ovo; o anterior fica guardado com
  o XP, a fase e as necessidades dele, **pausado**, e volta igualzinho quando você troca de novo.
- Clima, Claude Code, monitor e as opções do menu são os mesmos pra todos.
- Pra ver sem trocar: `python main.py --demo --pet coruja` (ou `dragao`, `tubarao`, `pinguim`, `pato`, `fenix`;
  dá pra juntar com `--fase`).
- Novos bichos entram em `pet/especies.py` (nome, fases e jeito) e `pet/pixelart.py` (pele, proporções e
  detalhes como asas e cauda); as poses e as roupas são reaproveitadas.

## 🌦 Clima

<p align="center"><img src="docs/roupas.png" alt="Óculos escuros no sol, normal no nublado, guarda-chuva e galochas na chuva, gorro e cachecol na neve, cachecol no frio, pijama de noite e escondido na trovoada"></p>

Ele olha o céu de **Florianópolis, SC** pelo [Open-Meteo](https://open-meteo.com/) (grátis, sem chave),
a cada 30 minutos, numa thread separada. Sem internet, continua com o último clima que conseguiu.

| Lá fora | O Clawd |
|---|---|
| ☀ Céu limpo (de dia) | Óculos escuros, e a felicidade sobe em vez de cair |
| 🥵 Acima de 30 °C | Um ventiladorzinho girando do lado dele |
| ☁ Nublado | Normal |
| 🌫 Neblina | Anda devagarinho |
| 🌧 Chuva ou garoa | Guarda-chuva, galochas e gotas caindo na tela; fica preguiçoso e cochila mais |
| ❄ Neve | Gorro e cachecol |
| ⛈ Trovoada | Se esconde atrás da barra de tarefas, tremendo: **"Tá trovejando! 😱"** |
| 🥶 Abaixo de 15 °C | Cachecol em qualquer tempo, e a fome cai mais rápido |
| 🌙 De noite | Pijama listrado com touca |

- **Previsão:** de manhã (entre 6h e 12h), uma vez por dia, ele avisa se vai chover mais tarde, olhando a
  chance de chuva hora a hora: *"☔ Previsão: deve chover lá pelas 14h (59%)"*.
- **Ver o tempo:** clique nele, ou menu → **Clima**, pra ver temperatura, sensação, vento e chance de chuva.
- **Trocar a cidade:** menu → **Clima e cidade** → Trocar cidade (ex.: `Recife, PE`). Lá também dá pra
  desligar as gotas na tela e forçar uma atualização.
- As gotas ficam numa janela transparente que **os cliques atravessam**, então não atrapalham nada (e
  gastam uns 3% de um núcleo da CPU).

## 🤖 Integração com o Claude Code

<p align="center"><img src="docs/reacoes.png" alt="Comendo, digitando, comemorando, acenando, caído, facepalm e empanturrado"></p>

| No Claude Code | O Clawd |
|---|---|
| Você manda um prompt | Come o prompt 🍤 e fica digitando concentrado até o Claude terminar |
| A task termina | Pula, toca um som, ganha XP e diz **"Terminei! Gastei X tokens"** |
| O Claude espera você (permissão, pergunta) | Acena sem parar com **"Preciso de você!"** até você voltar pro terminal |
| Um comando de teste passa | Comemora ✅ |
| Um comando de teste falha | Cai duro de costas 💀 |
| Um comando dá erro | Facepalm 🤦 |
| Você fica dias sem usar o Claude | Fica com fome e tristinho |

Testes reconhecidos: pytest, unittest, npm/pnpm/yarn/bun test, jest, vitest, go/cargo/dotnet/mvn/gradle test,
make test/check, Invoke-Pester e outros. Se a saída disser "2 failed", conta como falha mesmo com código 0.

### Tokens

- **Sessão:** soma o `usage` de cada resposta no transcript da sessão, contando cada mensagem uma vez só.
- **Task:** quanto a sessão cresceu entre o prompt e o fim.
- **Semana:** todos os transcripts de `%USERPROFILE%\.claude\projects\` dos últimos 7 dias. Arquivos parados não
  são nem abertos, e só o que foi acrescentado é relido.
- **Meta semanal** (menu → Claude Code): a partir de 80% ele fica empanturrado e sonolento; acima de 100% pede
  pra você descansar.
- **Só input e output** (menu → Claude Code): o cache costuma ser quase tudo; com essa opção ele conta só
  entrada + saída. Cada modo tem a sua meta.

> [!NOTE]
> É o uso **deste PC** nos últimos 7 dias, calculado a partir dos transcripts locais. **Não é** o limite
> oficial do seu plano, que aparece no `/usage` do Claude Code.

### Como funciona por baixo

```powershell
python instalar_hooks.py            # instala/atualiza em %USERPROFILE%\.claude\settings.json
python instalar_hooks.py --remover  # tira só os hooks do Clawd
```

O instalador mantém o resto do `settings.json` (seus outros hooks inclusive) e guarda um backup em
`settings.json.bak-pet`. Os hooks (`UserPromptSubmit`, `Stop`, `Notification`, `PostToolUse` e
`PostToolUseFailure`) chamam `pythonw.exe hooks\pet_hook.py` direto, sem shell no meio, então funcionam em
qualquer pasta de projeto. Confira em `/hooks` dentro do Claude Code.

O script do hook grava em `%USERPROFILE%\.claude\`:

| Arquivo | Pra quê |
|---|---|
| `pet-eventos.jsonl` | Um evento por linha; o pet lê os novos a cada segundo |
| `pet-status.json` | O último evento, com os tokens da sessão |
| `pet-cache\` | Soma parcial de tokens de cada sessão (pra não reler o transcript inteiro) |
| `pet-hook-erros.log` | Se algo der errado; o hook nunca atrapalha o Claude Code |

Mudou a pasta do projeto ou o Python? Rode o instalador de novo (ou menu → Claude Code → Reinstalar hooks)
e recrie o atalho com `python criar_atalho.py`.

## 🎨 Sprites próprios

Enquanto não houver PNGs, o Clawd é desenhado em pixel direto no código (`pet/pixelart.py`). Pra trocar,
crie uma pasta por animação com os quadros em PNG de fundo transparente, virados pra direita:

```
sprites/
├── parado/        01.png 02.png ...      ← Clawd adulto
├── andando/   dormindo/   pendurado/   caindo/   comendo/   comemorando/
├── acenando/  escondido/  tonto/       espirrando/
├── digitando/ caido/      mao_na_cabeca/  empanturrado/  tremendo/
├── ovo/<animacao>/                       ← cada fase pode ter as suas (+ chocando/ no ovo)
├── filhote/<animacao>/
└── anciao/<animacao>/
```

- Os quadros tocam em ordem alfabética. Um `anim.json` opcional define a velocidade: `{"ms": 120}`.
- O tamanho é ajustado sozinho pra ~70 px de altura, com zoom inteiro (sem borrar).
- Use transparência total ou nenhuma, sem semitransparência, senão aparece um contorno escuro.
- Animação sem pasta continua com o desenho provisório.
- As roupas do clima são desenhadas por cima do provisório; com PNG próprio, ele fica sem elas.
- Outros pets usam o mesmo esquema dentro da pasta deles: `sprites/<bicho>/<fase>/<animacao>/` (ex.: `sprites/coruja/`).

O ícone e as imagens deste README saem da mesma pixel art: `python ferramentas/gerar_imagens.py`
(essa ferramenta precisa do Pillow: `pip install pillow`).

## 🧪 Testes

```powershell
python -m unittest discover -s tests -t .
```

São 198 testes: física, mouse, save, regras do tamagotchi, monitores, o script do hook rodando de verdade,
contagem de tokens, o menu, os pets, o clima (com uma resposta real do Open-Meteo, sem acessar a rede) e as reações
do Clawd. Os que abrem janela usam uma pasta temporária no lugar do seu `~/.claude`.

## 🗂 Estrutura

<details>
<summary>Ver os arquivos</summary>

```
main.py               ponto de entrada (python main.py [--demo])
pet.pyw               abre sem terminal (é o que o atalho usa)
criar_atalho.py       cria o atalho com ícone na área de trabalho / Menu Iniciar
instalar_hooks.py     instala/remove os hooks no settings.json
hooks/
  pet_hook.py         o script que o Claude Code chama em cada evento
pet/
  mascote.py          janela, ações, mouse e loop de animação
  menu.py             menu do clique direito
  painel.py           janela de Status e tokens
  balao.py            balão de fala
  efeitos.py          coração, Zzz, migalhas, bolhas, gotas, estrelinhas e mosquinhas
  tamagotchi.py       avisos, sono, espirros, banho e XP
  necessidades.py     regras do tamagotchi: taxas, gripe, tempo offline, fases (sem Tk)
  clima.py            Open-Meteo, códigos de tempo, roupas e previsão (regras sem Tk)
  clima_controle.py   busca o clima numa thread, veste, faz chover e avisa da previsão
  chuva.py            gotas de chuva numa janela que os cliques atravessam
  claude_code.py      lê os eventos dos hooks, reações, meta e tokens da semana
  eventos_claude.py   traduz o JSON do hook em eventos do Clawd (sem Tk)
  tokens.py           soma de tokens dos transcripts (sem Tk)
  fisica.py           gravidade, arremesso e quiques (sem Tk)
  interacao.py        clique x arrasto, velocidade do arremesso, sacudida (sem Tk)
  sprites.py          carrega PNGs ou o desenho provisório
  pixelart.py         toda a pixel art: os sete bichos em cada fase, roupas, efeitos, ícones
  especies.py         os pets, o jeito de cada um e a troca entre eles (progresso separado)
  estado.py           save em pet.json
  sons.py             sonzinhos com winsound
  tela.py             API do Windows: DPI, monitores, tempo ocioso, janela em foco
  config.py           todos os números ajustáveis
assets/               ícone do programa
docs/                 imagens deste README
ferramentas/          gerador do ícone e das imagens
tests/
```

O save fica em `pet.json` e os erros em `pet.log`, ambos na pasta do projeto (fora do git).
</details>

## 🗺 Roadmap

- [x] **Fase 1:** janela transparente, andar, clique, menu, arrastar, arremessar e tontura
- [x] **Fase 2:** necessidades, tempo offline, avisos, gripe, banho e evolução
- [x] **Fase 3:** hooks do Claude Code, contador de tokens e meta semanal
- [x] **Fase 4:** clima de verdade (Open-Meteo), roupinhas pelo tempo, chuva na tela e previsão
- [x] **Extra:** troca de pet: dragãozinho, tubarãozinho, pinguinzinho, patinho de borracha, fênix e corujinha
- [ ] **Fase 5:** loja de acessórios, fiscal do git, hora de dormir, datas especiais, música e conversa com o Claude

<div align="center">
<sub>Feito com 🧡 e muitos tokens. Clawd é o mascote do <a href="https://claude.com/claude-code">Claude Code</a>.</sub>
</div>
