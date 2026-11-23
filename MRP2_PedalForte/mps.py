"""Plano Mestre de Producao - MPS (RF07).

Formato em ``dados["mps"]``::

    {"PA-001": [10, 30, 0, 40, 25, 0, 35, 30], ...}

Cada lista tem ``HORIZONTE`` (8) posicoes: demanda do produto acabado em
cada semana do horizonte de planejamento.
"""

from itens import listar_itens, obter_item
from utils import (
    HORIZONTE,
    ErroNegocio,
    arredondar,
    formatar_numero,
    montar_tabela,
    validar_numero,
    validar_semana,
)


def _obter_pa(dados, codigo):
    """Obtem o item garantindo que e um produto acabado."""
    item = obter_item(dados, codigo)
    if item["tipo"] != "PA":
        raise ErroNegocio(
            f"{item['codigo']} nao e produto acabado: o MPS contem apenas "
            "itens PA.")
    return item


def obter_plano(dados, codigo):
    """Demanda semanal de um PA (lista com HORIZONTE posicoes)."""
    plano = dados["mps"].get(codigo)
    if plano is None:
        return [0.0] * HORIZONTE
    return list(plano) + [0.0] * (HORIZONTE - len(plano))


def definir_demanda(dados, codigo, semana, quantidade):
    """Define (ou altera) a demanda de um PA em uma semana."""
    item = _obter_pa(dados, codigo)
    validar_semana(semana)
    validar_numero(quantidade, "A demanda", minimo=0)
    plano = obter_plano(dados, item["codigo"])
    plano[semana - 1] = arredondar(quantidade)
    dados["mps"][item["codigo"]] = plano


def definir_plano(dados, codigo, quantidades):
    """Define a demanda das 8 semanas de uma so vez."""
    item = _obter_pa(dados, codigo)
    if len(quantidades) != HORIZONTE:
        raise ErroNegocio(f"informe exatamente {HORIZONTE} quantidades.")
    for quantidade in quantidades:
        validar_numero(quantidade, "A demanda", minimo=0)
    dados["mps"][item["codigo"]] = [arredondar(q) for q in quantidades]


def formatar_mps(dados):
    """Tabela do MPS: uma linha por produto acabado."""
    pas = listar_itens(dados, "PA")
    if not pas:
        return ["Nenhum produto acabado cadastrado."]
    cabecalho = ["Item"] + [f"S{s}" for s in range(1, HORIZONTE + 1)]
    cabecalho.append("Total")
    linhas = []
    for item in pas:
        plano = obter_plano(dados, item["codigo"])
        linhas.append([f"{item['codigo']} {item['descricao']}"]
                      + [formatar_numero(q) for q in plano]
                      + [formatar_numero(sum(plano))])
    return montar_tabela(cabecalho, linhas, "<" + ">" * (HORIZONTE + 1))
