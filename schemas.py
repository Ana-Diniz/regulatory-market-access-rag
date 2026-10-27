"""Typed extraction output; provenance is audited separately."""
from typing import Literal

from pydantic import BaseModel, Field


class CampoTexto(BaseModel):
    valor: str | None = Field(description="Valor extraído ou null se ausente")
    fonte_id: str | None = Field(description="Identificador F1, F2 etc. ou null")
    trecho: str | None = Field(description="Trecho literal curto da fonte ou null")


class CampoDesfecho(CampoTexto):
    valor: Literal["Favorável", "Desfavorável", "Condicionado"] | None = Field(
        description="Recomendação normalizada ou null se não identificável"
    )


class CampoAno(CampoTexto):
    valor: int | None = Field(ge=1900, le=2100, description="Ano da publicação ou null")


class DecisaoRegulatoria(BaseModel):
    tecnologia_avaliada: CampoTexto
    desfecho: CampoDesfecho
    ano_decisao: CampoAno
