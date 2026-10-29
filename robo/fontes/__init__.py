from . import icarros, mercadolivre, olx, webmotors

FONTES = {
    "olx": olx.buscar,
    "webmotors": webmotors.buscar,
    "mercadolivre": mercadolivre.buscar,
    "icarros": icarros.buscar,
}
