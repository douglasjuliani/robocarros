import json

from robo import filtro, notificacao, ranking
from robo.fontes import icarros, mercadolivre, olx, webmotors
from robo.modelo import Anuncio, Busca, numero, uf_de

BUSCA = Busca(nome="Civic", marca="Honda", modelo="Civic", preco_min=60000, preco_max=110000,
              ano_min=2017, km_max=90000, uf="SC", excluir=["leilão", "sinistro"])


def test_utilitarios():
    assert numero("R$ 89.900") == 89900
    assert numero("R$ 89.900,50") == 89900
    assert numero("80.000 km") == 80000
    assert uf_de("Santa Catarina") == "SC" and uf_de("sp") == "SP" and uf_de("São Paulo") == "SP"


def test_filtro():
    ok = Anuncio("olx", "1", "Honda Civic EXL 2.0", "u", 95000, 2019, 50000, "Florianópolis", "SC")
    assert filtro.aceita(ok, BUSCA)
    for mudanca in [dict(preco=150000), dict(ano=2014), dict(km=120000), dict(uf="SP"),
                    dict(titulo="Honda Civic LEILÃO"), dict(titulo="Honda Fit")]:
        assert not filtro.aceita(Anuncio(**{**ok.__dict__, **mudanca}), BUSCA), mudanca
    # dado ausente não elimina o anúncio
    assert filtro.aceita(Anuncio("olx", "2", "Civic", "u"), BUSCA)


def test_olx():
    dados = {"props": {"pageProps": {"ads": [
        {"subject": "Honda Civic EXL", "url": "https://sc.olx.com.br/x/1", "listId": 1, "price": "R$ 89.900",
         "properties": [{"name": "regdate", "value": "2019"}, {"name": "mileage", "value": "45000"}],
         "locationDetails": {"municipality": "Florianópolis", "uf": "SC"}},
        {"advertisingId": "banner"}]}}}
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(dados)}</script>'
    [a] = olx.extrair(html)
    assert (a.preco, a.ano, a.km, a.uf, a.id) == (89900, 2019, 45000, "SC", "1")
    assert "estado-sc" in olx.montar_url(BUSCA, 2) and "o=2" in olx.montar_url(BUSCA, 2)


def test_webmotors():
    dados = {"SearchResults": [{"UniqueId": 555, "Specification": {
        "Title": "HONDA CIVIC 2.0 EXL", "Make": {"Value": "HONDA"}, "Model": {"Value": "CIVIC"},
        "Version": {"Value": "2.0 EXL CVT"}, "YearFabrication": "2019", "YearModel": 2020.0, "Odometer": 30000.0, "NumberPorts": "4"},
        "Prices": {"Price": 105000.0}, "Seller": {"City": "Joinville", "State": "Santa Catarina (SC)"}}]}
    [a] = webmotors.extrair(dados)
    assert (a.preco, a.ano, a.ano_fab, a.km, a.id) == (105000, 2020, 2019, 30000, "555")
    assert a.url.endswith("/honda/civic/2-0-exl-cvt/4-portas/2020/555")
    assert "honda%2Fcivic" in webmotors.montar_url(BUSCA, 1)


def test_mercadolivre():
    dados = {"results": [{"id": "MLB1", "title": "Honda Civic", "permalink": "https://ml/1", "price": 88000,
        "attributes": [{"id": "VEHICLE_YEAR", "value_name": "2018"}, {"id": "KILOMETERS", "value_name": "70000 km"}],
        "location": {"city": {"name": "Blumenau"}, "state": {"name": "Santa Catarina"}}}]}
    [a] = mercadolivre.extrair(dados)
    assert (a.preco, a.ano, a.km, a.uf) == (88000, 2018, 70000, "SC")
    assert "price=60000-110000" in mercadolivre.montar_url(BUSCA, 1)


def test_icarros_jsonld_e_cards():
    ld = {"@type": "ItemList", "itemListElement": [{"item": {"@type": "Car", "name": "Honda Civic",
          "url": "/comprar/x/honda/civic/d12345678", "offers": {"price": "92000"},
          "vehicleModelDate": "2019", "mileageFromOdometer": {"value": "40000"}}}]}
    [a] = icarros.extrair(f'<script type="application/ld+json">{json.dumps(ld)}</script>')
    assert (a.preco, a.ano, a.km, a.id) == (92000, 2019, 40000, "12345678")
    html = '<li><a href="/comprar/sc/honda/civic/d87654321" title="Honda Civic EXL">x</a> R$ 95.000 2020 30.000 km</li>'
    [b] = icarros.extrair(html)
    assert (b.preco, b.ano, b.km) == (95000, 2020, 30000)
    assert icarros.montar_url(BUSCA, 1).endswith("/comprar/santa-catarina/honda/civic")


def test_email():
    a = Anuncio("olx", "1", "Honda Civic <EXL>", "https://x", 89900, 2019, 45000, "Florianópolis", "SC")
    b = Anuncio("olx", "2", "Honda Civic", "https://y", 100000, 2019, 1000)
    c = Anuncio("olx", "3", "Honda Civic", "https://z", 110000, 2019, 1000)
    lista = ranking.calcular([("Civic", x) for x in (c, a, b)], {"olx:1"})
    assunto, texto, html = notificacao.montar([("Civic", a)], lista, primeira_vez=False, limite=2)
    assert assunto == "🚗 1 carro(s) novo(s) encontrado(s)"
    assert "1. 🆕 Honda Civic <EXL> | R$ 89.900 (-10.1% vs média R$ 99.967)" in texto and "mais 1 anúncio" in texto
    assert "&lt;EXL&gt;" in html and html.count("<td>1</td>") == 1


def test_ranking():
    def ad(i, preco, ano):
        return ("Duster", Anuncio("webmotors", str(i), "Renault Duster", "u", preco, ano, 1000))
    itens = [ad(1, 100000, 2023), ad(2, 110000, 2023), ad(3, 120000, 2023), ad(4, 90000, 2022), ad(5, 60000, 2024)]
    lista = ranking.calcular(itens)
    # 2023 tem 3 anúncios: média própria (110 mil); os outros usam a média geral (96 mil)
    assert [it["anuncio"].id for it in lista] == ["5", "1", "4", "2", "3"]
    assert lista[1]["media"] == 110000 and lista[0]["media"] == 96000
    assert lista[0]["suspeito"] and not lista[1]["suspeito"]
    assert "| 1 | [Renault Duster](u) ⚠️ |" in ranking.markdown(lista, "hoje")
    # com motor no título, compara 1.6 com 1.6 e 1.3 com 1.3
    def ad2(i, preco, mot):
        return ("D", Anuncio("olx", str(i), f"Duster {mot}", "u", preco, 2024, 1000))
    l2 = ranking.calcular([ad2(1, 90, "1.6"), ad2(2, 100, "1.6"), ad2(3, 110, "1.6"),
                           ad2(4, 130, "1.3"), ad2(5, 140, "1.3"), ad2(6, 150, "1.3")])
    assert {it["anuncio"].id: it["media"] for it in l2} == {"1": 100, "2": 100, "3": 100, "4": 140, "5": 140, "6": 140}


def test_cambio():
    b = Busca(nome="Duster", modelo="Duster", cambio="automatico")
    assert filtro.aceita(Anuncio("webmotors", "1", "RENAULT DUSTER 1.6 ICONIC CVT", "u", cambio="Automática"), b)
    assert not filtro.aceita(Anuncio("webmotors", "2", "RENAULT DUSTER 1.6 ZEN", "u", cambio="Manual"), b)
    assert filtro.aceita(Anuncio("olx", "3", "Renault Duster Intense 1.6 CVT", "u"), b)
    assert not filtro.aceita(Anuncio("olx", "4", "Renault Duster Zen 1.6", "u"), b)  # câmbio desconhecido


def test_olx_cards():
    html = ('<div class="olx-adcard__content"><a data-testid="adcard-link" title="Renault Duster Iconic 1.3 TB Aut. 2023" '
            'href="https://rs.olx.com.br/x/autos-e-pecas/carros-vans-e-utilitarios/renault-duster-2023-1548636195">t</a>'
            '<div aria-label="41000 quilômetros rodados">41.000 km</div><span>R$ 89.000</span><span>Online</span>'
            '<span>Novo Hamburgo, Centro</span></div>')
    [a] = olx.extrair(html)
    assert (a.id, a.preco, a.ano, a.km, a.cidade, a.uf) == ("1548636195", 89000, 2023, 41000, "Novo Hamburgo", "RS")
    assert filtro.aceita(a, Busca(nome="D", modelo="Duster", cambio="automatico"))


def test_ranking_junta_duplicados_e_ano_fabricacao():
    wm = Anuncio("webmotors", "1", "Duster", "u1", 85990, 2026, 31791, ano_fab=2025)
    ox = Anuncio("olx", "2", "Duster", "u2", 86500, 2026, 31791)
    outro = Anuncio("olx", "3", "Duster", "u3", 120000, 2026, 30000)
    lista = ranking.calcular([("D", x) for x in (ox, wm, outro)])
    assert [it["anuncio"].id for it in lista] == ["1", "3"] and lista[0]["outros_sites"] == ["olx"]
    b = Busca(nome="D", ano_min=2026)
    assert not filtro.aceita(wm, b) and filtro.aceita(ox, b)  # fabricação 2025 < 2026
