"""Typed extraction output; provenance is audited separately."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CampoTexto(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valor: str | None = Field(description="Valor extraído ou null se ausente")
    fonte_id: str | None = Field(
        pattern=r"^F[1-9][0-9]*$",
        description="Identificador F1, F2 etc. ou null",
    )
    trecho: str | None = Field(description="Trecho literal curto da fonte ou null")


class CampoDesfecho(CampoTexto):
    valor: Literal["Favorável", "Desfavorável", "Condicionado"] | None = Field(
        description="Recomendação normalizada ou null se não identificável"
    )


class CampoAno(CampoTexto):
    valor: int | None = Field(
        strict=True,
        ge=1900,
        le=2100,
        description="Ano inteiro comprovado pelo trecho ou null",
    )


class DecisaoRegulatoria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tecnologia_avaliada: CampoTexto = Field(
        description="Nome da tecnologia (por exemplo, Bedaquilina), sem população ou indicação."
    )
    indicacao_clinica: CampoTexto = Field(
        description="Indicação clínica/população-alvo, separada do nome da tecnologia."
    )
    desfecho: CampoDesfecho
    ano_relatorio: CampoAno = Field(
        description="Ano de publicação do relatório, não presumido como ano da decisão."
    )
    ano_decisao: CampoAno = Field(
        description="Ano da deliberação ou decisão, somente com evidência específica; caso contrário null."
    )
