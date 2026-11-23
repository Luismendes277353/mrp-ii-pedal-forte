"""Estrutura de produto - BOM (RF03, RN03).

Formato em ``dados["estrutura"]``::

    {"PA-001": [{"componente": "SA-010", "quantidade": 1.0}, ...], ...}

A explosao da BOM e feita de forma recursiva. A regra de hierarquia de tipos
(PA -> SA/MP, SA -> MP, MP sem estrutura) limita a arvore a 3 niveis e
impede ciclos.
"""

from itens import obter_item
from utils import (
    ErroNegocio,
    arredondar,
    formatar_numero,
    validar_numero,
)

NIVEL_MAXIMO = 2  # niveis 0 (pai), 1 e 2: PA -> SA -> MP
TIPOS_PERMITIDOS = {"PA": ("SA", "MP"), "SA": ("MP",)}


def componentes_de(dados, codigo):
    """Lista de componentes diretos (dicionarios) de um item."""
    return dados["estrutura"].get(codigo, [])


def validar_componente(dados, pai, componente, quantidade):
    """Aplica as regras RN01 e RN03 a um par pai/componente."""
    item_pai = obter_item(dados, pai)
    item_comp = obter_item(dados, componente)
    if item_pai["tipo"] == "MP":
        raise ErroNegocio(
            f"{pai} e materia-prima (item comprado) e nao possui estrutura "
            "(RN03).")
    if pai == componente:
        raise ErroNegocio("um item nao pode ser componente de si mesmo.")
    permitidos = TIPOS_PERMITIDOS[item_pai["tipo"]]
    if item_comp["tipo"] not in permitidos:
        raise ErroNegocio(
            f"componente invalido (RN03): um {item_pai['tipo']} so pode ter "
            f"componentes do tipo {' ou '.join(permitidos)}, mas "
            f"{componente} e {item_comp['tipo']}.")
    validar_numero(quantidade, "A quantidade por unidade", maior_que=0)


def adicionar_componente(dados, pai, componente, quantidade):
    """Inclui um componente na BOM do pai (ou atualiza a quantidade).

    Retorna 'incluido' ou 'atualizado'.
    """
    pai = pai.strip().upper()
    componente = componente.strip().upper()
    validar_componente(dados, pai, componente, quantidade)
    lista = dados["estrutura"].setdefault(pai, [])
    for linha in lista:
        if linha["componente"] == componente:
            linha["quantidade"] = arredondar(quantidade)
            return "atualizado"
    lista.append({"componente": componente,
                  "quantidade": arredondar(quantidade)})
    return "incluido"


def remover_componente(dados, pai, componente):
    """Remove um componente da BOM do pai."""
    pai = pai.strip().upper()
    componente = componente.strip().upper()
    lista = dados["estrutura"].get(pai, [])
    for linha in lista:
        if linha["componente"] == componente:
            lista.remove(linha)
            if not lista:
                del dados["estrutura"][pai]
            return
    raise ErroNegocio(f"{componente} nao e componente de {pai}.")


def mapa_pais(dados):
    """Inverte a BOM: {componente: [(pai, quantidade_por_unidade), ...]}."""
    mapa = {}
    for pai, lista in dados["estrutura"].items():
        for linha in lista:
            mapa.setdefault(linha["componente"], []).append(
                (pai, linha["quantidade"]))
    return mapa


def montar_arvore(dados, codigo, prefixo="", nivel=1):
    """Explosao recursiva da BOM.

    Devolve uma lista de tuplas ``(nivel, prefixo_visual, componente,
    quantidade)`` na ordem de impressao da arvore indentada.
    """
    filhos = componentes_de(dados, codigo)
    if filhos and nivel > NIVEL_MAXIMO:
        raise ErroNegocio(
            "estrutura com mais de 3 niveis ou com ciclo (dados "
            "inconsistentes).")
    linhas = []
    for posicao, filho in enumerate(filhos):
        ultimo = posicao == len(filhos) - 1
        conector = "└── " if ultimo else "├── "
        linhas.append((nivel, prefixo + conector, filho["componente"],
                       filho["quantidade"]))
        extensao = "    " if ultimo else "│   "
        linhas.extend(montar_arvore(dados, filho["componente"],
                                    prefixo + extensao, nivel + 1))
    return linhas


def formatar_bom(dados, codigo):
    """Texto da BOM indentada (explosao) com o nivel de cada componente."""
    item = obter_item(dados, codigo)
    if item["tipo"] == "MP":
        raise ErroNegocio(f"{item['codigo']} e materia-prima e nao possui "
                          "estrutura.")
    arvore = montar_arvore(dados, item["codigo"])
    saida = [f"{item['codigo']} {item['descricao']}"]
    if not arvore:
        saida.append("(sem componentes cadastrados)")
        return saida

    textos = []
    for _, prefixo, comp, _ in arvore:
        descricao = obter_item(dados, comp)["descricao"]
        textos.append(f"{prefixo}{comp} {descricao}")
    largura = max(len(texto) for texto in textos) + 2

    niveis = {0: [item["codigo"]]}
    for (nivel, _, comp, qtd), texto in zip(arvore, textos):
        unidade = obter_item(dados, comp)["unidade"]
        pontos = "." * (largura - len(texto))
        saida.append(f"{texto} {pontos} {formatar_numero(qtd)} {unidade}"
                     f"  [nivel {nivel}]")
        if comp not in niveis.setdefault(nivel, []):
            niveis[nivel].append(comp)

    resumo = " | ".join(f"{nivel} = {', '.join(codigos)}"
                        for nivel, codigos in sorted(niveis.items()))
    saida.append("")
    saida.append(f"Niveis: {resumo}")
    return saida
