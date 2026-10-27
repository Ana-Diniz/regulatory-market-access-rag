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
        description="Ano inteiro da publicação ou null",
    )


class DecisaoRegulatoria(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tecnologia_avaliada: CampoTexto
    desfecho: CampoDesfecho
    ano_decisao: CampoAno
