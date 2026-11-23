"""Cadastro de itens (RF02, RN01).

Estrutura de cada item em ``dados["itens"][codigo]``::

    {"codigo": "SA-020", "descricao": "...", "tipo": "SA", "unidade": "un",
     "custo_unitario": 0.0, "lead_time": 1, "estoque_seguranca": 10.0,
     "lote_minimo": 80.0}
"""

from utils import (
    TIPOS_FABRICADOS,
    TIPOS_ITEM,
    ErroNegocio,
    arredondar,
    formatar_moeda,
    formatar_numero,
    montar_tabela,
    validar_codigo_item,
    validar_numero,
)

CAMPOS_ALTERAVEIS = (
    "descricao",
    "unidade",
    "custo_unitario",
    "lead_time",
    "estoque_seguranca",
    "lote_minimo",
)


def tipo_do_codigo(codigo):
    """Extrai o tipo (PA, SA ou MP) do codigo do item."""
    return codigo.split("-")[0]


def eh_fabricado(item):
    """PA e SA sao fabricados; MP e comprada (RN01)."""
    return item["tipo"] in TIPOS_FABRICADOS


def obter_item(dados, codigo):
    """Busca um item pelo codigo ou levanta ErroNegocio."""
    codigo = str(codigo).strip().upper()
    try:
        return dados["itens"][codigo]
    except KeyError:
        raise ErroNegocio(f"item {codigo} nao cadastrado.") from None


def _validar_campos(descricao, unidade, custo_unitario, lead_time,
                    estoque_seguranca, lote_minimo):
    """Valida e normaliza os campos de um item."""
    descricao = str(descricao).strip()
    unidade = str(unidade).strip()
    if not descricao:
        raise ErroNegocio("a descricao do item e obrigatoria.")
    if not unidade:
        raise ErroNegocio("a unidade de medida do item e obrigatoria.")
    validar_numero(custo_unitario, "O custo unitario", minimo=0)
    validar_numero(lead_time, "O lead time", minimo=0)
    if int(lead_time) != lead_time:
        raise ErroNegocio("o lead time deve ser um numero inteiro de semanas.")
    validar_numero(estoque_seguranca, "O estoque de seguranca", minimo=0)
    validar_numero(lote_minimo, "O lote minimo", minimo=0)
    return {
        "descricao": descricao,
        "unidade": unidade,
        "custo_unitario": arredondar(custo_unitario),
        "lead_time": int(lead_time),
        "estoque_seguranca": arredondar(estoque_seguranca),
        "lote_minimo": arredondar(lote_minimo),
    }


def cadastrar_item(dados, codigo, descricao, unidade, custo_unitario,
                   lead_time, estoque_seguranca, lote_minimo):
    """Cadastra um novo item. O tipo e derivado do codigo (RN01)."""
    codigo = validar_codigo_item(codigo)
    if codigo in dados["itens"]:
        raise ErroNegocio(f"ja existe um item com o codigo {codigo} (RN01).")
    campos = _validar_campos(descricao, unidade, custo_unitario, lead_time,
                             estoque_seguranca, lote_minimo)
    item = {"codigo": codigo, "tipo": tipo_do_codigo(codigo)}
    item.update(campos)
    dados["itens"][codigo] = item
    dados["estoque"].setdefault(codigo, 0.0)
    return item


def alterar_item(dados, codigo, alteracoes):
    """Altera campos de um item existente.

    Codigo e tipo nao podem ser alterados, pois a estrutura de produto e o
    historico de estoque dependem deles.
    """
    item = obter_item(dados, codigo)
    invalidos = set(alteracoes) - set(CAMPOS_ALTERAVEIS)
    if invalidos:
        raise ErroNegocio(
            f"campos nao alteraveis: {', '.join(sorted(invalidos))}.")
    novos = {campo: item[campo] for campo in CAMPOS_ALTERAVEIS}
    novos.update(alteracoes)
    item.update(_validar_campos(
        novos["descricao"], novos["unidade"], novos["custo_unitario"],
        novos["lead_time"], novos["estoque_seguranca"], novos["lote_minimo"]))
    return item


def listar_itens(dados, tipo=None):
    """Lista de itens ordenada por tipo (PA, SA, MP) e codigo."""
    if tipo is not None and tipo not in TIPOS_ITEM:
        raise ErroNegocio(f"tipo '{tipo}' invalido. Use PA, SA ou MP.")
    itens = [item for item in dados["itens"].values()
             if tipo is None or item["tipo"] == tipo]
    return sorted(itens, key=lambda i: (TIPOS_ITEM.index(i["tipo"]),
                                        i["codigo"]))


def formatar_itens(dados, tipo=None):
    """Tabela de texto com os itens cadastrados."""
    itens = listar_itens(dados, tipo)
    if not itens:
        return ["Nenhum item cadastrado."]
    linhas = [
        (i["codigo"], i["descricao"], i["tipo"], i["unidade"],
         formatar_moeda(i["custo_unitario"]), i["lead_time"],
         formatar_numero(i["estoque_seguranca"]),
         formatar_numero(i["lote_minimo"]))
        for i in itens
    ]
    cabecalho = ("Codigo", "Descricao", "Tipo", "Un", "Custo un.",
                 "LT(sem)", "Est.Seg.", "Lote min.")
    return montar_tabela(cabecalho, linhas, "<<<<>>>>")