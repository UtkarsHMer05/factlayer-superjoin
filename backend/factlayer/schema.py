from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Value(BaseModel):
    kind: Literal['number', 'text', 'date', 'boolean', 'entity', 'range']
    raw: str
    number: str | None = None
    upper: str | None = None
    unit: str | None = None
    scale: Literal['one', 'thousand', 'lakh', 'million', 'crore', 'billion'] = 'one'
    comparator: Literal['=', '>', '>=', '<', '<='] = '='
    precision: int | None = Field(default=None, ge=0, le=12)

    @model_validator(mode='after')
    def numeric(self):
        if self.kind in ('number', 'range'):
            if self.number is None or not Decimal(self.number.replace(',', '')).is_finite():
                raise ValueError('Numeric claims require a finite decimal string')
            if self.kind == 'range' and (self.upper is None or not Decimal(self.upper).is_finite() or Decimal(self.upper) < Decimal(self.number)):
                raise ValueError('Range requires a finite upper bound >= lower bound')
        return self


class Anchor(BaseModel):
    unit_id: str
    quote: str = Field(min_length=1)
    role: Literal['assertion', 'subject', 'value', 'header', 'context'] = 'assertion'


class Claim(BaseModel):
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    assertion: str = Field(min_length=1)
    value: Value
    context: dict[str, str | None] = Field(default_factory=dict)
    context_evidence: dict[str, list[Anchor]] = Field(default_factory=dict)
    evidence: list[Anchor] = Field(min_length=1)
    polarity: Literal['positive', 'negative'] = 'positive'
    modality: Literal['asserted', 'estimate', 'forecast', 'possible'] = 'asserted'


class Extraction(BaseModel):
    title: str = ''
    subject: str = ''
    claims: list[Claim] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
