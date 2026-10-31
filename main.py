"""Inicia o pet de desktop. Uso: python main.py [--demo [--fase ovo|filhote|clawd|anciao] [--pet <bicho>]]"""

import argparse
import logging

from pet import config, especies, tela, tokens


def migrar_nomes_antigos():
    """Renomeia os arquivos de quando o projeto era só o Clawd (clawd.json, clawd-eventos.jsonl...)."""
    claude = tokens.pasta_claude()
    pares = [(config.PASTA_BASE / "clawd.json", config.ARQUIVO_ESTADO),
             (config.PASTA_BASE / "clawd.log", config.ARQUIVO_LOG),
             (claude / "clawd-eventos.jsonl", claude / "pet-eventos.jsonl"),
             (claude / "clawd-status.json", claude / "pet-status.json"),
             (claude / "clawd-cache", claude / "pet-cache"),
             (claude / "clawd-hook-erros.log", claude / "pet-hook-erros.log")]
    for velho, novo in pares:
        if velho.exists() and not novo.exists():
            try:
                velho.rename(novo)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description="Pet de desktop (Clawd e a turma)")
    parser.add_argument("--demo", action="store_true", help="mostra todas as animações e não salva")
    parser.add_argument("--fase", choices=("ovo", "filhote", "clawd", "anciao"),
                        help="na demo, mostra essa fase de evolução")
    parser.add_argument("--pet", choices=sorted(especies.ESPECIES), help="na demo, mostra esse pet")
    args = parser.parse_args()

    migrar_nomes_antigos()
    logging.basicConfig(filename=config.ARQUIVO_LOG, encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # Só um pet por vez (a variável precisa viver até o fim pro mutex não fechar)
    trava = tela.instancia_unica("Local\\PetDeDesktop")
    if trava is None:
        print("O pet já está rodando.")
        return

    from pet.mascote import Mascote
    Mascote(demo=args.demo, fase_demo=args.fase if args.demo else None,
            pet_demo=args.pet if args.demo else None).rodar()


if __name__ == "__main__":
    main()
