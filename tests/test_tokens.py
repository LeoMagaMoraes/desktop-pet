import os
import tempfile
import time
import unittest
from pathlib import Path

from clawd import eventos_claude as ev
from clawd import tokens
from tests.test_hook import resposta


class TestNumeros(unittest.TestCase):
    def test_formatar(self):
        self.assertEqual(tokens.formatar(950), "950")
        self.assertEqual(tokens.formatar(12_345), "12.3k")
        self.assertEqual(tokens.formatar(4_500_000), "4.5M")
        self.assertEqual(tokens.formatar(2_100_000_000), "2.1B")

    def test_ler_numero(self):
        self.assertEqual(tokens.ler_numero("20M"), 20_000_000)
        self.assertEqual(tokens.ler_numero("1,5m"), 1_500_000)
        self.assertEqual(tokens.ler_numero("800k"), 800_000)
        self.assertEqual(tokens.ler_numero("123456"), 123_456)
        self.assertIsNone(tokens.ler_numero(""))
        self.assertIsNone(tokens.ler_numero("0"))
        with self.assertRaises(ValueError):
            tokens.ler_numero("muito")

    def test_total_e_so_io(self):
        t = {"entrada": 10, "saida": 20, "cache_criacao": 300, "cache_leitura": 4000}
        self.assertEqual(tokens.total(t), 4330)
        self.assertEqual(tokens.total(t, so_io=True), 30)

    def test_extrair_ignora_o_que_nao_e_resposta(self):
        self.assertIsNone(tokens.extrair('{"type":"user","message":{"content":"oi"}}'))
        self.assertIsNone(tokens.extrair("lixo"))
        ident, ts, t = tokens.extrair(resposta("m1", 1, 2, 3))
        self.assertEqual((ident, t["saida"], t["cache_leitura"]), ("m1", 2, 3))
        self.assertGreater(ts, 0)


class TestSessao(unittest.TestCase):
    def test_incremental_e_sem_repetir(self):
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "s.jsonl"
            arq.write_text(resposta("a", 1, 10) + "\n" + resposta("a", 1, 10) + "\n", encoding="utf-8")
            cache = tokens.atualizar_sessao(arq, {})
            self.assertEqual(cache["tokens"]["saida"], 10)
            # Linha pela metade no fim (o Claude ainda está escrevendo) fica pra depois
            with open(arq, "a", encoding="utf-8") as f:
                f.write(resposta("a", 1, 10) + "\n" + resposta("b", 1, 5)[:30])
            cache = tokens.atualizar_sessao(arq, cache)
            self.assertEqual(cache["tokens"]["saida"], 10)
            with open(arq, "a", encoding="utf-8") as f:
                f.write(resposta("b", 1, 5)[30:] + "\n")
            cache = tokens.atualizar_sessao(arq, cache)
            self.assertEqual(cache["tokens"]["saida"], 15)

    def test_arquivo_reescrito_recomeca(self):
        with tempfile.TemporaryDirectory() as pasta:
            arq = Path(pasta) / "s.jsonl"
            arq.write_text((resposta("a", 1, 10) + "\n") * 5, encoding="utf-8")
            cache = tokens.atualizar_sessao(arq, {})
            arq.write_text(resposta("z", 1, 7) + "\n", encoding="utf-8")
            self.assertEqual(tokens.atualizar_sessao(arq, cache)["tokens"]["saida"], 7)


class TestSemana(unittest.TestCase):
    def test_soma_7_dias_sem_repetir_entre_arquivos(self):
        agora = time.time()
        recente = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(agora - 3600))
        antigo = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(agora - 9 * 86400))
        with tempfile.TemporaryDirectory() as pasta:
            p = Path(pasta)
            (p / "proj1").mkdir()
            (p / "proj1" / "a.jsonl").write_text(
                resposta("m1", 1, 100, ts=recente) + "\n" + resposta("velha", 1, 999, ts=antigo) + "\n",
                encoding="utf-8")
            # Sessão retomada copia a mensagem m1 pro arquivo novo: não pode contar duas vezes
            (p / "proj1" / "sub").mkdir()
            (p / "proj1" / "sub" / "b.jsonl").write_text(
                resposta("m1", 1, 100, ts=recente) + "\n" + resposta("m2", 1, 50, ts=recente) + "\n",
                encoding="utf-8")
            # Arquivo parado há 10 dias nem é lido
            velho = p / "proj1" / "velho.jsonl"
            velho.write_text(resposta("m9", 1, 7777, ts=recente) + "\n", encoding="utf-8")
            os.utime(velho, (agora - 10 * 86400, agora - 10 * 86400))

            contador = tokens.ContadorSemana(p)
            self.assertEqual(contador.contar(agora)["saida"], 150)
            # Segunda contagem só lê o que foi acrescentado
            with open(p / "proj1" / "a.jsonl", "a", encoding="utf-8") as f:
                f.write(resposta("m3", 1, 25, ts=recente) + "\n")
            self.assertEqual(contador.contar(agora)["saida"], 175)
            self.assertGreater(contador.ultima_atividade, agora - 60)


class TestClassificar(unittest.TestCase):
    def test_comandos_de_teste(self):
        for c in ("pytest -q", "python -m unittest discover", "npm test", "npm run test -- --watch=false",
                  "pnpm test", "go test ./...", "cargo test", "dotnet test", "./gradlew test",
                  "mvn test", "npx jest", "Invoke-Pester", "make check"):
            self.assertTrue(ev.eh_teste(c), c)
        for c in ("ls", "git commit -m 'fix tests'", "pip install pytest", "npm install jest",
                  "cat test_x.py", "echo testing"):
            self.assertFalse(ev.eh_teste(c), c)

    def test_saida_com_falha_mesmo_com_codigo_zero(self):
        dados = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                 "tool_input": {"command": "pytest | tail -3"},
                 "tool_response": {"stdout": "=== 2 failed, 10 passed in 1.2s ===", "stderr": ""}}
        self.assertFalse(ev.classificar(dados)["passou"])
        dados["tool_response"]["stdout"] = "=== 0 failed, 12 passed ==="
        self.assertTrue(ev.classificar(dados)["passou"])
        dados["tool_response"] = {"stdout": "", "stderr": "Ran 5 tests\n\nFAILED (failures=1)"}
        self.assertFalse(ev.classificar(dados)["passou"])

    def test_interrupcao_nao_conta_como_erro(self):
        self.assertIsNone(ev.classificar({"hook_event_name": "PostToolUseFailure", "tool_name": "Bash",
                                          "tool_input": {"command": "ls"}, "is_interrupt": True}))

    def test_notificacao_que_nao_pede_nada(self):
        r = ev.classificar({"hook_event_name": "Notification", "notification_type": "auth_success"})
        self.assertFalse(r["esperando"])


if __name__ == "__main__":
    unittest.main()
