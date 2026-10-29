import json

from robo import filtro, whatsapp
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
        "Version": {"Value": "2.0 EXL CVT"}, "YearModel": 2020.0, "Odometer": 30000.0, "NumberPorts": "4"},
        "Prices": {"Price": 105000.0}, "Seller": {"City": "Joinville", "State": "Santa Catarina (SC)"}}]}
    [a] = webmotors.extrair(dados)
    assert (a.preco, a.ano, a.km, a.id) == (105000, 2020, 30000, "555")
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


def test_mensagem():
    a = Anuncio("olx", "1", "Honda Civic", "https://x", 89900, 2019, 45000, "Florianópolis", "SC")
    assert "R$ 89.900 · 2019 · 45.000 km · Florianópolis/SC" in whatsapp.formatar(a, "Civic")
