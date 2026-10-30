"""Inicia o Clawd. Uso: python main.py [--demo]"""

import argparse
import logging

from clawd import config, tela


def main():
    parser = argparse.ArgumentParser(description="Clawd, mascote de desktop")
    parser.add_argument("--demo", action="store_true", help="mostra todas as animações e não salva")
    args = parser.parse_args()

    logging.basicConfig(filename=config.ARQUIVO_LOG, encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Só um Clawd por vez (a variável precisa viver até o fim pro mutex não fechar)
    trava = tela.instancia_unica("Local\\ClawdMascoteDesktop")
    if trava is None:
        print("O Clawd já está rodando.")
        return

    from clawd.mascote import Mascote
    Mascote(demo=args.demo).rodar()


if __name__ == "__main__":
    main()
