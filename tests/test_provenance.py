"""Unit tests for deterministic provenance; no LLM or network needed."""
import unittest
from types import SimpleNamespace

from provenance import auditar_extracao, preparar_contexto


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        documentos = [
            SimpleNamespace(
                page_content="Em 2020, a tecnologia bedaquilina foi avaliada. Recomendação: não incorporar.",
                metadata={"documento": "relatorio.pdf", "pagina": 7},
            )
        ]
        self.contexto, self.fontes = preparar_contexto(documentos)

    def test_context_includes_page_and_source_identifier(self):
        self.assertIn("[F1] Página: 7", self.contexto)
        self.assertEqual(self.fontes["F1"]["pagina"], 7)

    def test_local_file_path_is_not_sent_in_context(self):
        caminho = "/home/usuario/documentos/confidencial/relatorio.pdf"
        documentos = [
            SimpleNamespace(
                page_content="Trecho de exemplo para auditoria.",
                metadata={"documento": caminho, "pagina": 4},
            )
        ]
        contexto, fontes = preparar_contexto(documentos)
        self.assertIn("[F1] Página: 4", contexto)
        self.assertNotIn(caminho, contexto)
        self.assertNotIn("relatorio.pdf", contexto)
        # The local lookup still retains the original path for auditing.
        self.assertEqual(fontes["F1"]["documento"], caminho)
        self.assertEqual(fontes["F1"]["pagina"], 4)

    def test_quote_and_value_found(self):
        dados = {"ano_decisao": {"valor": 2020, "fonte_id": "F1", "trecho": "Em 2020, a tecnologia bedaquilina"}}
        auditado = auditar_extracao(dados, self.fontes)
        self.assertEqual(auditado["ano_decisao"]["status"], "trecho_localizado")
        self.assertEqual(auditado["ano_decisao"]["fonte"]["pagina"], 7)

    def test_unknown_source_is_not_confirmed(self):
        dados = {"tecnologia_avaliada": {"valor": "bedaquilina", "fonte_id": "F99", "trecho": "bedaquilina"}}
        resultado = auditar_extracao(dados, self.fontes)["tecnologia_avaliada"]
        self.assertEqual(resultado["status"], "sem_fonte_verificavel")
        self.assertIsNone(resultado["valor"])

    def test_hallucinated_quote_is_rejected(self):
        dados = {"ano_decisao": {"valor": 2022, "fonte_id": "F1", "trecho": "Publicado em 2022"}}
        self.assertEqual(auditar_extracao(dados, self.fontes)["ano_decisao"]["status"], "trecho_nao_localizado")

    def test_quote_must_contain_year(self):
        dados = {"ano_decisao": {"valor": 2022, "fonte_id": "F1", "trecho": "tecnologia bedaquilina foi avaliada"}}
        self.assertEqual(auditar_extracao(dados, self.fontes)["ano_decisao"]["status"], "valor_nao_localizado_no_trecho")

    def test_year_cannot_match_part_of_longer_number(self):
        fontes = {"F1": {**self.fontes["F1"], "texto": "Publicado em 20201. Publicado em 2020."}}
        dados = {"ano_decisao": {"valor": 2020, "fonte_id": "F1", "trecho": "Publicado em 20201"}}
        self.assertEqual(
            auditar_extracao(dados, fontes)["ano_decisao"]["status"],
            "valor_nao_localizado_no_trecho",
        )
        dados["ano_decisao"]["trecho"] = "Publicado em 2020."
        self.assertEqual(
            auditar_extracao(dados, fontes)["ano_decisao"]["status"],
            "trecho_localizado",
        )

    def test_technology_cannot_match_part_of_longer_word(self):
        fontes = {"F1": {**self.fontes["F1"], "texto": "Bedaquilinax não é bedaquilina."}}
        dados = {"tecnologia_avaliada": {"valor": "bedaquilina", "fonte_id": "F1", "trecho": "Bedaquilinax"}}
        self.assertEqual(
            auditar_extracao(dados, fontes)["tecnologia_avaliada"]["status"],
            "valor_nao_localizado_no_trecho",
        )
        dados["tecnologia_avaliada"]["trecho"] = "bedaquilina."
        self.assertEqual(
            auditar_extracao(dados, fontes)["tecnologia_avaliada"]["status"],
            "trecho_localizado",
        )

    def test_quote_must_not_be_substring_of_longer_source_token(self):
        casos = (
            ("ano_decisao", 2020, "2020", "Publicado em 20201."),
            ("tecnologia_avaliada", "bedaquilina", "bedaquilina", "A bedaquilinax foi avaliada."),
        )
        for campo, valor, trecho, texto_fonte in casos:
            with self.subTest(campo=campo):
                fontes = {"F1": {**self.fontes["F1"], "texto": texto_fonte}}
                dados = {campo: {"valor": valor, "fonte_id": "F1", "trecho": trecho}}
                resultado = auditar_extracao(dados, fontes)[campo]
                self.assertEqual(resultado["status"], "trecho_nao_localizado")
                self.assertIsNone(resultado["valor"])

    def test_missing_value(self):
        self.assertEqual(auditar_extracao({}, self.fontes)["desfecho"]["status"], "nao_encontrado")

    def test_missing_or_invalid_page_cannot_verify_quote(self):
        dados = {"tecnologia_avaliada": {"valor": "bedaquilina", "fonte_id": "F1", "trecho": "tecnologia bedaquilina"}}
        for pagina in (None, 0, -2, "7", True):
            with self.subTest(pagina=pagina):
                fonte = {**self.fontes["F1"], "pagina": pagina}
                resultado = auditar_extracao(dados, {"F1": fonte})["tecnologia_avaliada"]
                self.assertEqual(resultado["status"], "sem_fonte_verificavel")
                self.assertIsNone(resultado["fonte"])

    def test_unknown_document_cannot_verify_quote(self):
        dados = {"tecnologia_avaliada": {"valor": "bedaquilina", "fonte_id": "F1", "trecho": "tecnologia bedaquilina"}}
        for nome in ("", "   ", "desconhecido"):
            with self.subTest(nome=nome):
                fonte = {**self.fontes["F1"], "documento": nome}
                resultado = auditar_extracao(dados, {"F1": fonte})["tecnologia_avaliada"]
                self.assertEqual(resultado["status"], "sem_fonte_verificavel")


if __name__ == "__main__":
    unittest.main()
