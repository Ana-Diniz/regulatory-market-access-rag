"""Schema validation tests; entirely offline, no external APIs."""
import unittest

from pydantic import ValidationError

from schemas import DecisaoRegulatoria


def exemplo():
    return {
        "tecnologia_avaliada": {
            "valor": "Bedaquilina", "fonte_id": "F1", "trecho": "Bedaquilina"
        },
        "indicacao_clinica": {
            "valor": "tuberculose multirresistente",
            "fonte_id": "F2", "trecho": "pacientes com tuberculose multirresistente"
        },
        "desfecho": {
            "valor": "Condicionado", "fonte_id": "F3",
            "trecho": "incorporação condicionada à apresentação de dados"
        },
        "ano_relatorio": {
            "valor": 2020, "fonte_id": "F1", "trecho": "Agosto/2020"
        },
        "ano_decisao": {
            "valor": 2021, "fonte_id": "F3", "trecho": "deliberação de 2021"
        },
    }


class SchemaTests(unittest.TestCase):
    def test_valid_data_and_distinct_years(self):
        modelo = DecisaoRegulatoria.model_validate(exemplo())
        self.assertEqual(modelo.tecnologia_avaliada.valor, "Bedaquilina")
        self.assertEqual(modelo.indicacao_clinica.valor, "tuberculose multirresistente")
        self.assertEqual(modelo.ano_relatorio.valor, 2020)
        self.assertEqual(modelo.ano_decisao.valor, 2021)

    def test_invalid_outcome(self):
        dados = exemplo()
        dados["desfecho"]["valor"] = "Aprovado sem evidência"
        with self.assertRaises(ValidationError):
            DecisaoRegulatoria.model_validate(dados)

    def test_invalid_year(self):
        for campo in ("ano_relatorio", "ano_decisao"):
            with self.subTest(campo=campo):
                dados = exemplo()
                dados[campo]["valor"] = 1800
                with self.assertRaises(ValidationError):
                    DecisaoRegulatoria.model_validate(dados)

    def test_missing_data_allowed_explicitly(self):
        dados = exemplo()
        dados["ano_decisao"] = {"valor": None, "fonte_id": None, "trecho": None}
        self.assertIsNone(DecisaoRegulatoria.model_validate(dados).ano_decisao.valor)

    def test_indication_may_be_explicitly_unknown(self):
        dados = exemplo()
        dados["indicacao_clinica"] = {"valor": None, "fonte_id": None, "trecho": None}
        self.assertIsNone(DecisaoRegulatoria.model_validate(dados).indicacao_clinica.valor)

    def test_missing_field_is_rejected(self):
        for campo in ("indicacao_clinica", "ano_relatorio", "ano_decisao"):
            with self.subTest(campo=campo):
                dados = exemplo()
                del dados[campo]
                with self.assertRaises(ValidationError):
                    DecisaoRegulatoria.model_validate(dados)

    def test_year_string_is_not_silently_coerced(self):
        for campo in ("ano_relatorio", "ano_decisao"):
            with self.subTest(campo=campo):
                dados = exemplo()
                dados[campo]["valor"] = "2020"
                with self.assertRaises(ValidationError):
                    DecisaoRegulatoria.model_validate(dados)

    def test_malformed_source_identifier_is_rejected(self):
        for fonte_id in ("F0", "F-1", "7", "F01", ""):
            with self.subTest(fonte_id=fonte_id):
                dados = exemplo()
                dados["tecnologia_avaliada"]["fonte_id"] = fonte_id
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
