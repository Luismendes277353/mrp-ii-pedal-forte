"""Custo padrao dos itens fabricados - materiais + mao de obra (RF13).

O custo e calculado de forma recursiva, percorrendo a estrutura de produto:

    custo(MP)       = custo unitario cadastrado
    custo(PA ou SA) = soma(quantidade x custo(componente)) + mao de obra
    mao de obra     = tempo unitario do roteiro x custo-hora do centro
"""

from estrutura import componentes_de
from itens import eh_fabricado, listar_itens, obter_item
from utils import (
    ErroNegocio,
    formatar_moeda,
    formatar_numero,
    montar_tabela,
)


def mao_de_obra(dados, codigo):
    """Mao de obra direta do item (None se nao houver roteiro)."""
    roteiro = dados["roteiros"].get(codigo)
    if roteiro is None:
        return None
    centro = dados["centros"].get(roteiro["centro"])
    if centro is None:
        raise ErroNegocio(
            f"o roteiro de {codigo} usa o centro {roteiro['centro']}, que "
            "nao esta cadastrado.")
    return {
        "centro": centro["codigo"],
        "horas": roteiro["tempo_unitario"],
        "custo_hora": centro["custo_hora"],
        "valor": round(roteiro["tempo_unitario"] * centro["custo_hora"], 2),
    }


def custo_padrao(dados, codigo):
    """Custo padrao de um item, calculado recursivamente."""
    item = obter_item(dados, codigo)
    if not eh_fabricado(item):
        return item["custo_unitario"]
    total = 0.0
    for linha in componentes_de(dados, item["codigo"]):
        total += linha["quantidade"] * custo_padrao(dados,
                                                    linha["componente"])
    obra = mao_de_obra(dados, item["codigo"])
    if obra:
        total += obra["valor"]
    return round(total, 2)


def detalhar_custo(dados, codigo):
    """Composicao do custo padrao de um item fabricado.

    Retorna ``{"item", "linhas", "mao_de_obra", "total"}`` onde cada linha
    e um componente direto com seu custo unitario (padrao, se fabricado).
    """
    item = obter_item(dados, codigo)
    if not eh_fabricado(item):
        raise ErroNegocio(
            f"{item['codigo']} e materia-prima: o custo e o unitario "
            f"cadastrado (R$ {formatar_moeda(item['custo_unitario'])}).")
    linhas = []
    for linha in componentes_de(dados, item["codigo"]):
        componente = obter_item(dados, linha["componente"])
        unitario = custo_padrao(dados, componente["codigo"])
        linhas.append({
            "codigo": componente["codigo"],
            "descricao": componente["descricao"],
            "quantidade": linha["quantidade"],
            "custo_unitario": unitario,
            "total": round(linha["quantidade"] * unitario, 2),
        })
    return {"item": item, "linhas": linhas,
            "mao_de_obra": mao_de_obra(dados, item["codigo"]),
            "total": custo_padrao(dados, item["codigo"])}


def formatar_custo(dados, codigo):
    """Texto do custo padrao (mockup 6.7)."""
    detalhe = detalhar_custo(dados, codigo)
    item = detalhe["item"]
    linhas = [
        (c["codigo"], c["descricao"], formatar_numero(c["quantidade"]),
         formatar_moeda(c["custo_unitario"]), formatar_moeda(c["total"]))
        for c in detalhe["linhas"]
    ]
    obra = detalhe["mao_de_obra"]
    if obra:
        linhas.append(("Mao de obra", obra["centro"],
                       f"{formatar_numero(obra['horas'])} h",
                       formatar_moeda(obra["custo_hora"]),
                       formatar_moeda(obra["valor"])))
    saida = [f"CUSTO PADRAO - {item['codigo']} {item['descricao']}"]
    tabela = montar_tabela(("Item", "Descricao", "Qtde", "Custo un.",
                            "Total"), linhas, "<<>>>")
    saida.extend(tabela)
    saida.append("-" * max(len(t) for t in tabela))
    saida.append(f"CUSTO PADRAO TOTAL R$ {formatar_moeda(detalhe['total'])}")
    if not obra:
        saida.append("Obs.: item sem roteiro - mao de obra nao considerada.")
    return saida


def formatar_tabela_custos(dados):
    """Custo padrao de todos os itens fabricados x custo cadastrado."""
    linhas = []
    for item in listar_itens(dados):
        if eh_fabricado(item):
            linhas.append((item["codigo"], item["descricao"],
                           formatar_moeda(custo_padrao(dados,
                                                       item["codigo"])),
                           formatar_moeda(item["custo_unitario"])))
    return montar_tabela(("Item", "Descricao", "Custo padrao (R$)",
                          "Custo cadastrado (R$)"), linhas, "<<>>")


def atualizar_custos_unitarios(dados):
    """Grava o custo padrao como custo unitario dos itens fabricados.

    O calculo e recursivo a partir das MP, entao nao depende da ordem de
    atualizacao. Retorna a quantidade de itens atualizados.
    """
    total = 0
    for item in listar_itens(dados):
        if eh_fabricado(item):
            item["custo_unitario"] = custo_padrao(dados, item["codigo"])
            total += 1
    return total
