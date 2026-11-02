"""Save do pet em pet.json: status, XP, fase, acessórios, posição e horário do save."""

import copy
import json
import logging
import os
import time
from datetime import datetime

log = logging.getLogger(__name__)

PADRAO = {
    "versao": 1,
    "especie": "clawd",          # pet ativo; os outros ficam guardados em "pets"
    "pets": {},
    "status": {"fome": 80, "energia": 80, "felicidade": 80},   # 0 a 100, 100 = ótimo
    "xp": 0,
    "xp_gasto": 0,              # XP gasto na loja (a fase continua contando o XP total)
    "renascimentos": 0,         # quantas vezes a Fênix anciã escolheu renascer
    "fase": "ovo",
    "acessorios": {"comprados": [], "equipados": {}},   # da loja; equipados: lugar -> item
    "sujeira": 0,               # 0 = limpinho, 100 = cheio de mosquinha
    "doente": False,            # gripado até tomar remédio
    "horas_com_fome": 0.0,      # tempo seguido com fome baixa (leva à gripe)
    "modo_tamagotchi": True,    # desligado: status pausados, sem avisos
    "claude": {
        "so_io": False,                          # contar só input + output (sem cache)
        "meta_semanal": {"total": 150_000_000, "io": 1_500_000},   # None = sem meta
        "sons": True,
        "ultima_atividade": None,                # último evento do Claude Code (ISO)
        "dias_penalizados": 0,                   # dias sem Claude já descontados
        "tasks": 0,                              # tasks finalizadas desde sempre
        "historico": {},                         # "AAAA-MM-DD" -> resumo do dia
        "fiscal_git": True,                      # plaquinha "commit?" nos projetos do Claude
    },
    "rotina": {
        "hora_dormir": None,         # "HH:MM": depois disso ele te manda dormir
        "aniversario": None,         # "DD/MM": festa no seu aniversário
        "data_saudada": None,        # dia em que já comemorou a data especial
        "tela_cheia": True,          # some quando um programa abre em tela cheia
        "musica": True,              # põe o fone e dança quando tem som tocando
        "resumo_auto": True,         # resumo do dia às 18h
        "resumo_mostrado": None,     # dia em que o resumo automático já apareceu
    },
    "atualizacao": {
        "ultima_checagem": None,     # dia em que já olhou se tem versão nova no GitHub
        "acabou_de_atualizar": None, # títulos das novidades, pra contar depois de reiniciar
    },
    "hoje": None,                    # contadores do resumo do dia (carinhos, minutos no PC...)
    "clima": {
        "cidade": "Florianópolis",
        "estado": "Santa Catarina",
        "pais": "BR",
        "nome_exibido": None,
        "lat": None,                 # achados uma vez pela API de geocoding
        "lon": None,
        "utc_offset": -10800,
        "atual": None,               # último clima que conseguiu (usado sem internet)
        "atualizado": None,
        "previsao_avisada": None,    # dia em que já avisou da chuva de manhã
    },
    "andar_nas_janelas": True,  # pousa, passeia e pula em cima das janelas abertas
    "lembretes": [],            # [{"id", "texto", "quando" (ISO), "repetir": None ou "diario"}]
    "monitor": None,            # nome do monitor onde ele mora (ex.: \\.\DISPLAY2)
    "lugar_favorito": None,     # onde foi solto por último {"x", "y"}
    "ultima_posicao": None,     # onde estava quando salvou {"x", "y"}
    "ultimo_save": None,        # ISO 8601 com fuso
}


def _arredondar(valor):
    """Copia arredondando números quebrados pra o save ficar legível."""
    if isinstance(valor, dict):
        return {k: _arredondar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_arredondar(v) for v in valor]
    if isinstance(valor, float):
        return round(valor, 3)
    return valor


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
                log.error("pet.json ilegível (%s); começando do zero", erro)
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
        texto = json.dumps(_arredondar(self.dados), indent=2, ensure_ascii=False)
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
