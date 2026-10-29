"""Filtro aplicado localmente a todos os anúncios, independente da plataforma.

Os sites nem sempre respeitam todos os filtros da URL, então tudo é conferido aqui.
Anúncios sem a informação (ex.: km não informado) não são descartados por ela.
"""
from __future__ import annotations

from .modelo import Anuncio, Busca, normalizar


def aceita(a: Anuncio, b: Busca) -> bool:
    titulo = normalizar(a.titulo)

    if b.modelo and normalizar(b.modelo) not in titulo:
        return False
    if a.preco is not None:
        if b.preco_min and a.preco < b.preco_min:
            return False
        if b.preco_max and a.preco > b.preco_max:
            return False
    if a.ano is not None:
        if b.ano_min and a.ano < b.ano_min:
            return False
        if b.ano_max and a.ano > b.ano_max:
            return False
    if a.km is not None and b.km_max and a.km > b.km_max:
        return False
    if b.uf and a.uf and a.uf != b.uf:
        return False
    if b.cidades and a.cidade and normalizar(a.cidade) not in {normalizar(c) for c in b.cidades}:
        return False
    if any(normalizar(p) not in titulo for p in b.incluir):
        return False
    if any(normalizar(p) in titulo for p in b.excluir):
        return False
    return True
