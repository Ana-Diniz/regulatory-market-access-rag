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
        self.assertIn("[F1] Documento: relatorio.pdf | Página: 7", self.contexto)
        self.assertEqual(self.fontes["F1"]["pagina"], 7)

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
