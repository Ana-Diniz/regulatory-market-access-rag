"""Schema validation tests, no external API calls."""
import unittest

from pydantic import ValidationError

from schemas import DecisaoRegulatoria


def exemplo():
    return {
        "tecnologia_avaliada": {"valor": "bedaquilina", "fonte_id": "F1", "trecho": "tecnologia bedaquilina"},
        "desfecho": {"valor": "Desfavorável", "fonte_id": "F1", "trecho": "não incorporar"},
        "ano_decisao": {"valor": 2020, "fonte_id": "F1", "trecho": "Em 2020"},
    }


class SchemaTests(unittest.TestCase):
    def test_valid_data(self):
        self.assertEqual(DecisaoRegulatoria.model_validate(exemplo()).ano_decisao.valor, 2020)

    def test_invalid_outcome(self):
        dados = exemplo()
        dados["desfecho"]["valor"] = "Aprovado sem evidência"
        with self.assertRaises(ValidationError):
            DecisaoRegulatoria.model_validate(dados)

    def test_invalid_year(self):
        dados = exemplo()
        dados["ano_decisao"]["valor"] = 1800
        with self.assertRaises(ValidationError):
            DecisaoRegulatoria.model_validate(dados)

    def test_missing_data_allowed_explicitly(self):
        dados = exemplo()
        dados["ano_decisao"] = {"valor": None, "fonte_id": None, "trecho": None}
        self.assertIsNone(DecisaoRegulatoria.model_validate(dados).ano_decisao.valor)

    def test_year_string_is_not_silently_coerced(self):
        dados = exemplo()
        dados["ano_decisao"]["valor"] = "2020"
        with self.assertRaises(ValidationError):
            DecisaoRegulatoria.model_validate(dados)

    def test_malformed_source_identifier_is_rejected(self):
        for fonte_id in ("F0", "F-1", "7", "F01", ""):
            with self.subTest(fonte_id=fonte_id):
                dados = exemplo()
                dados["tecnologia_avaliada"]["fonte_id"] = fonte_id
                if fonte_id == "F01":
                    # F01 is syntactically rejected to avoid ambiguous aliases.
                    pass
                with self.assertRaises(ValidationError):
                    DecisaoRegulatoria.model_validate(dados)

    def test_unexpected_nested_fields_are_rejected(self):
        dados = exemplo()
        dados["desfecho"]["confianca"] = 0.99
        with self.assertRaises(ValidationError):
            DecisaoRegulatoria.model_validate(dados)

    def test_unexpected_top_level_fields_are_rejected(self):
        dados = exemplo()
        dados["resumo"] = "Sem fonte"
        with self.assertRaises(ValidationError):
            DecisaoRegulatoria.model_validate(dados)


if __name__ == "__main__":
    unittest.main()
