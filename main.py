"""Inicia o Clawd. Uso: python main.py [--demo [--fase ovo|filhote|clawd|anciao]]"""

import argparse
import logging

from clawd import config, tela


def main():
    parser = argparse.ArgumentParser(description="Clawd, mascote de desktop")
    parser.add_argument("--demo", action="store_true", help="mostra todas as animações e não salva")
    parser.add_argument("--fase", choices=("ovo", "filhote", "clawd", "anciao"),
                        help="na demo, mostra essa fase de evolução")
    args = parser.parse_args()

    logging.basicConfig(filename=config.ARQUIVO_LOG, encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Só um Clawd por vez (a variável precisa viver até o fim pro mutex não fechar)
    trava = tela.instancia_unica("Local\\ClawdMascoteDesktop")
    if trava is None:
        print("O Clawd já está rodando.")
        return

    from clawd.mascote import Mascote
    Mascote(demo=args.demo, fase_demo=args.fase if args.demo else None).rodar()


if __name__ == "__main__":
    main()
