from rest_framework.pagination import PageNumberPagination as DRFPageNumberPagination


class PageNumberPagination(DRFPageNumberPagination):
    page_size = 20
    # A tela Radar pede a fila inteira numa pagina so (page_size=120). Um teto
    # menor que isso nao devolve erro: corta a lista em silencio, e o contador
    # do header passa a discordar do numero de cartoes na tela.
    max_page_size = 200
    page_size_query_param = "page_size"
