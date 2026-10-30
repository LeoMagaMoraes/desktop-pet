import json
import tempfile
import unittest
from pathlib import Path

from clawd.estado import PADRAO, Estado


class TestEstado(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo = Path(self.pasta.name) / "clawd.json"

    def tearDown(self):
        self.pasta.cleanup()

    def test_sem_arquivo_usa_padrao(self):
        e = Estado.carregar(self.arquivo)
        self.assertEqual(e.dados, PADRAO)
        self.assertIsNot(e.dados["status"], PADRAO["status"])   # cópia, não o padrão em si

    def test_salvar_e_carregar(self):
        e = Estado.carregar(self.arquivo)
        e.ajustar_status("fome", -30)
        e.dados["lugar_favorito"] = {"x": 300, "y": 1020}
        self.assertTrue(e.salvar())
        e2 = Estado.carregar(self.arquivo)
        self.assertEqual(e2.status["fome"], 50)
        self.assertEqual(e2.dados["lugar_favorito"], {"x": 300, "y": 1020})
        self.assertIsNotNone(e2.dados["ultimo_save"])
        self.assertFalse(self.arquivo.with_name("clawd.json.tmp").exists())

    def test_save_antigo_ganha_chaves_novas(self):
        self.arquivo.write_text(json.dumps({"status": {"fome": 10}, "xp": 50}), encoding="utf-8")
        e = Estado.carregar(self.arquivo)
        self.assertEqual(e.status["fome"], 10)
        self.assertEqual(e.status["energia"], PADRAO["status"]["energia"])
        self.assertEqual(e.dados["xp"], 50)
        self.assertIn("acessorios", e.dados)

    def test_arquivo_corrompido_vira_backup(self):
        self.arquivo.write_text("{isso não é json", encoding="utf-8")
        e = Estado.carregar(self.arquivo)
        self.assertEqual(e.dados, PADRAO)
        self.assertTrue(self.arquivo.with_name("clawd.json.corrompido").exists())

    def test_status_fica_entre_0_e_100(self):
        e = Estado.carregar(self.arquivo)
        self.assertEqual(e.ajustar_status("felicidade", 500), 100)
        self.assertEqual(e.ajustar_status("felicidade", -500), 0)


if __name__ == "__main__":
    unittest.main()
