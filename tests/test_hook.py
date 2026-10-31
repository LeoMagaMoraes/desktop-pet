"""Roda o hooks/pet_hook.py de verdade, mandando o JSON pela entrada como o Claude Code faz."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "hooks" / "pet_hook.py"


def resposta(ident, entrada, saida, cache_leitura=0, ts="2026-10-30T12:00:00.000Z"):
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {
        "id": ident, "type": "message", "role": "assistant", "content": [],
        "usage": {"input_tokens": entrada, "output_tokens": saida,
                  "cache_creation_input_tokens": 0, "cache_read_input_tokens": cache_leitura}}})


class TestHook(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.base = Path(self.pasta.name)
        self.transcript = self.base / "sessao.jsonl"
        self.transcript.write_text(resposta("m1", 10, 100) + "\n", encoding="utf-8")

    def tearDown(self):
        self.pasta.cleanup()

    def hook(self, dados, cru=None):
        env = dict(os.environ, PET_PASTA_CLAUDE=str(self.base))
        entrada = cru if cru is not None else json.dumps(dados).encode("utf-8")
        r = subprocess.run([sys.executable, str(SCRIPT)], input=entrada, capture_output=True,
                           env=env, timeout=30)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, b"")      # nada na saída (iria pro contexto do Claude)
        return r

    def eventos(self):
        log = self.base / "pet-eventos.jsonl"
        if not log.exists():
            return []
        return [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]

    def comum(self, **kw):
        return dict({"session_id": "s-1", "transcript_path": str(self.transcript),
                     "cwd": r"C:\proj\meuapp"}, **kw)

    def test_task_completa_conta_tokens(self):
        self.hook(self.comum(hook_event_name="UserPromptSubmit", prompt="oi"))
        # O Claude responde: uma mensagem nova repetida em 3 linhas (conta 1 vez)
        with open(self.transcript, "a", encoding="utf-8") as f:
            for _ in range(3):
                f.write(resposta("m2", 5, 300, cache_leitura=1000) + "\n")
        self.hook(self.comum(hook_event_name="Stop"))

        prompt, fim = self.eventos()
        self.assertEqual(prompt["evento"], "prompt")
        self.assertEqual(prompt["projeto"], "meuapp")
        self.assertEqual(prompt["tokens_sessao"]["saida"], 100)
        self.assertEqual(fim["evento"], "fim")
        self.assertEqual(fim["tokens_task"], {"entrada": 5, "saida": 300, "cache_criacao": 0,
                                              "cache_leitura": 1000})
        self.assertEqual(fim["tokens_sessao"]["saida"], 400)
        status = json.loads((self.base / "pet-status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["id"], fim["id"])

    def test_fim_sem_prompt_nao_inventa_tokens_da_task(self):
        self.hook(self.comum(hook_event_name="Stop"))
        self.assertIsNone(self.eventos()[0]["tokens_task"])

    def test_teste_falhou_e_erro_de_comando(self):
        self.hook(self.comum(hook_event_name="PostToolUseFailure", tool_name="Bash",
                             tool_input={"command": "python -m pytest -q"}, error="Exit code 1\n2 failed"))
        self.hook(self.comum(hook_event_name="PostToolUse", tool_name="PowerShell",
                             tool_input={"command": "npm test"},
                             tool_response={"stdout": "Tests: 12 passed", "stderr": ""}))
        self.hook(self.comum(hook_event_name="PostToolUseFailure", tool_name="Bash",
                             tool_input={"command": "git psuh"}, error="Exit code 1\nnot a git command"))
        falhou, passou, erro = self.eventos()
        self.assertEqual((falhou["evento"], falhou["passou"]), ("teste", False))
        self.assertEqual((passou["evento"], passou["passou"]), ("teste", True))
        self.assertEqual((erro["evento"], erro["codigo"]), ("erro", 1))

    def test_comando_comum_nao_vira_evento(self):
        self.hook(self.comum(hook_event_name="PostToolUse", tool_name="Bash",
                             tool_input={"command": "ls"}, tool_response={"stdout": "a"}))
        self.hook(self.comum(hook_event_name="PostToolUse", tool_name="Edit",
                             tool_input={"file_path": "x"}, tool_response={}))
        self.assertEqual(self.eventos(), [])

    def test_notificacao(self):
        self.hook(self.comum(hook_event_name="Notification", notification_type="permission_prompt",
                             message="Claude needs your permission to use Bash"))
        ev = self.eventos()[0]
        self.assertEqual(ev["evento"], "notificacao")
        self.assertTrue(ev["esperando"])

    def test_entrada_quebrada_nao_quebra_o_claude(self):
        self.hook(None, cru=b"isso nao e json")
        self.hook(None, cru=b"")
        self.assertEqual(self.eventos(), [])

    def test_caminhos_com_acento_e_espaco(self):
        pasta = self.base / "Área de Trabalho"
        pasta.mkdir()
        transcript = pasta / "sessão.jsonl"
        transcript.write_text(resposta("x", 1, 2) + "\n", encoding="utf-8")
        self.hook({"hook_event_name": "UserPromptSubmit", "session_id": "s-2",
                   "transcript_path": str(transcript), "cwd": str(pasta)})
        self.assertEqual(self.eventos()[0]["tokens_sessao"]["saida"], 2)
        self.assertEqual(self.eventos()[0]["projeto"], "Área de Trabalho")


if __name__ == "__main__":
    unittest.main()
