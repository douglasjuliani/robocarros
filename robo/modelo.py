"""Estruturas de dados e utilitários compartilhados pelas fontes."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

UFS = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo", "SE": "Sergipe",
    "TO": "Tocantins",
}
_NOME_PARA_UF = {}


def normalizar(texto: str | None) -> str:
    """Minúsculas, sem acentos e com espaços simples."""
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto).strip().lower()


def slug(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", normalizar(texto)).strip("-")


def uf_de(texto: str | None) -> str | None:
    """Converte 'SC', 'Santa Catarina' etc. para a sigla da UF."""
    if not texto:
        return None
    if not _NOME_PARA_UF:
        _NOME_PARA_UF.update({normalizar(n): s for s, n in UFS.items()})
    t = texto.strip()
    if t.upper() in UFS:
        return t.upper()
    return _NOME_PARA_UF.get(normalizar(t))


def numero(valor) -> int | None:
    """Extrai um inteiro de 'R$ 89.900', '80.000 km', 89900.0 etc."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return int(valor)
    texto = str(valor).split(",")[0]  # descarta centavos
    digitos = re.sub(r"\D", "", texto)
    return int(digitos) if digitos else None


@dataclass
class Busca:
    nome: str
    marca: str = ""
    modelo: str = ""
    termo: str = ""
    preco_min: int | None = None
    preco_max: int | None = None
    ano_min: int | None = None
    ano_max: int | None = None
    km_max: int | None = None
    uf: str | None = None
    cidades: list[str] = field(default_factory=list)
    incluir: list[str] = field(default_factory=list)
    excluir: list[str] = field(default_factory=list)
    fontes: list[str] = field(default_factory=list)

    @property
    def texto_busca(self) -> str:
        return self.termo or f"{self.marca} {self.modelo}".strip()


@dataclass
class Anuncio:
    fonte: str
    id: str
    titulo: str
    url: str
    preco: int | None = None
    ano: int | None = None
    km: int | None = None
    cidade: str | None = None
    uf: str | None = None

    @property
    def chave(self) -> str:
        return f"{self.fonte}:{self.id}"
