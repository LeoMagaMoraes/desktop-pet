"""Save do Clawd em clawd.json: status, XP, fase, acessórios, posição e horário do save."""

import copy
import json
import logging
import os
import time
from datetime import datetime

log = logging.getLogger(__name__)

PADRAO = {
    "versao": 1,
    "status": {"fome": 80, "energia": 80, "felicidade": 80},   # 0 a 100, 100 = ótimo
    "xp": 0,
    "fase": "ovo",
    "acessorios": {"comprados": [], "equipados": {}},
    "lugar_favorito": None,     # onde foi solto por último {"x", "y"}
    "ultima_posicao": None,     # onde estava quando salvou {"x", "y"}
    "ultimo_save": None,        # ISO 8601 com fuso
}


def _mesclar(base, novo):
    """Copia `novo` por cima de `base`, mantendo chaves padrão que o save antigo não tem."""
    for chave, valor in novo.items():
        if isinstance(base.get(chave), dict) and isinstance(valor, dict):
            _mesclar(base[chave], valor)
        else:
            base[chave] = valor


class Estado:
    def __init__(self, caminho, dados):
        self.caminho = caminho
        self.dados = dados

    @classmethod
    def carregar(cls, caminho):
        dados = copy.deepcopy(PADRAO)
        if caminho.exists():
            try:
                lido = json.loads(caminho.read_text(encoding="utf-8"))
                if isinstance(lido, dict):
                    _mesclar(dados, lido)
            except (OSError, ValueError) as erro:
                # Save estragado: guarda uma cópia pra não perder e começa do padrão
                log.error("clawd.json ilegível (%s); começando do zero", erro)
                try:
                    caminho.replace(caminho.with_name(caminho.name + ".corrompido"))
                except OSError:
                    pass
        return cls(caminho, dados)

    @property
    def status(self):
        return self.dados["status"]

    def ajustar_status(self, nome, delta):
        """Soma delta ao status e mantém entre 0 e 100."""
        valor = max(0, min(100, self.status[nome] + delta))
        self.status[nome] = valor
        return valor

    def salvar(self):
        """Grava num .tmp e troca de uma vez, pra nunca deixar o save pela metade."""
        self.dados["ultimo_save"] = datetime.now().astimezone().isoformat(timespec="seconds")
        temporario = self.caminho.with_name(self.caminho.name + ".tmp")
        texto = json.dumps(self.dados, indent=2, ensure_ascii=False)
        for tentativa in range(3):
            try:
                temporario.write_text(texto, encoding="utf-8")
                os.replace(temporario, self.caminho)
                return True
            except OSError as erro:
                # O OneDrive às vezes segura o arquivo por um instante
                log.warning("Falha ao salvar (tentativa %d): %s", tentativa + 1, erro)
                time.sleep(0.1)
        return False
