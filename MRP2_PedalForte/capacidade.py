"""Centros de trabalho, roteiros e carga x capacidade - CRP (RF06, RF12).

* ``dados["centros"]``  -> ``{"CT-03": {"codigo", "descricao",
  "capacidade", "custo_hora"}}`` (capacidade em horas/semana)
* ``dados["roteiros"]`` -> ``{"SA-020": {"centro": "CT-02",
  "tempo_unitario": 0.8}}`` (roteiro de operacao unica, horas/unidade)
"""

from itens import eh_fabricado, listar_itens, obter_item
from ordens import ENCERRADA
from utils import (
    HORIZONTE,
    ErroNegocio,
    arredondar,
    formatar_decimal,
    formatar_moeda,
    formatar_numero,
    montar_tabela,
    validar_codigo_centro,
    validar_numero,
)


def obter_centro(dados, codigo):
    """Busca um centro de trabalho ou levanta ErroNegocio."""
    codigo = str(codigo).strip().upper()
    try:
        return dados["centros"][codigo]
    except KeyError:
        raise ErroNegocio(
            f"centro de trabalho {codigo} nao cadastrado.") from None


def _validar_centro(descricao, capacidade, custo_hora):
    descricao = str(descricao).strip()
    if not descricao:
        raise ErroNegocio("a descricao do centro e obrigatoria.")
    validar_numero(capacidade, "A capacidade", maior_que=0)
    validar_numero(custo_hora, "O custo-hora", minimo=0)
    return descricao, arredondar(capacidade), arredondar(custo_hora)


def cadastrar_centro(dados, codigo, descricao, capacidade, custo_hora):
    """Cadastra um centro de trabalho (capacidade em horas/semana)."""
    codigo = validar_codigo_centro(codigo)
    if codigo in dados["centros"]:
        raise ErroNegocio(f"ja existe o centro de trabalho {codigo}.")
    descricao, capacidade, custo_hora = _validar_centro(
        descricao, capacidade, custo_hora)
    centro = {"codigo": codigo, "descricao": descricao,
              "capacidade": capacidade, "custo_hora": custo_hora}
    dados["centros"][codigo] = centro
    return centro


def alterar_centro(dados, codigo, descricao, capacidade, custo_hora):
    """Altera os dados de um centro de trabalho existente."""
    centro = obter_centro(dados, codigo)
    descricao, capacidade, custo_hora = _validar_centro(
        descricao, capacidade, custo_hora)
    centro.update({"descricao": descricao, "capacidade": capacidade,
                   "custo_hora": custo_hora})
    return centro


def formatar_centros(dados):
    """Tabela dos centros de trabalho."""
    if not dados["centros"]:
        return ["Nenhum centro de trabalho cadastrado."]
    linhas = [
        (c["codigo"], c["descricao"], formatar_numero(c["capacidade"]),
         formatar_moeda(c["custo_hora"]))
        for c in sorted(dados["centros"].values(), key=lambda c: c["codigo"])
    ]
    return montar_tabela(("Codigo", "Descricao", "Capac.(h/sem)",
                          "Custo-hora (R$)"), linhas, "<<>>")


def definir_roteiro(dados, codigo_item, codigo_centro, tempo_unitario):
    """Define o centro que produz o item e o tempo por unidade (RF06)."""
    item = obter_item(dados, codigo_item)
    if not eh_fabricado(item):
        raise ErroNegocio(
            f"{item['codigo']} e materia-prima: apenas itens fabricados "
            "(PA/SA) possuem roteiro.")
    centro = obter_centro(dados, codigo_centro)
    validar_numero(tempo_unitario, "O tempo por unidade", maior_que=0)
    dados["roteiros"][item["codigo"]] = {
        "centro": centro["codigo"],
        "tempo_unitario": arredondar(tempo_unitario),
    }


def obter_roteiro(dados, codigo_item):
    """Roteiro do item ou None se nao houver."""
    return dados["roteiros"].get(codigo_item)


def itens_fabricados_sem_roteiro(dados):
    """Codigos de itens PA/SA que ainda nao tem roteiro."""
    return [i["codigo"] for i in listar_itens(dados)
            if eh_fabricado(i) and i["codigo"] not in dados["roteiros"]]


def formatar_roteiros(dados):
    """Tabela dos roteiros cadastrados."""
    if not dados["roteiros"]:
        return ["Nenhum roteiro cadastrado."]
    linhas = []
    for item in listar_itens(dados):
        roteiro = dados["roteiros"].get(item["codigo"])
        if roteiro:
            linhas.append((item["codigo"], item["descricao"],
                           roteiro["centro"],
                           formatar_numero(roteiro["tempo_unitario"])))
    return montar_tabela(("Item", "Descricao", "Centro", "Horas/un"),
                         linhas, "<<<>")


def calcular_carga(dados):
    """Carga semanal (horas) de cada centro (RN09).

    Soma, para cada OP nao encerrada com liberacao dentro do horizonte,
    ``quantidade x tempo unitario`` na semana de liberacao da ordem.
    Retorna ``{centro: [carga_s1, ..., carga_s8]}``.
    """
    carga = {codigo: [0.0] * HORIZONTE for codigo in dados["centros"]}
    for ordem in dados["ordens"]:
        if ordem["tipo"] != "OP" or ordem["status"] == ENCERRADA:
            continue
        roteiro = dados["roteiros"].get(ordem["item"])
        semana = ordem["semana_liberacao"]
        if roteiro is None or not 1 <= semana <= HORIZONTE:
            continue
        horas = ordem["quantidade"] * roteiro["tempo_unitario"]
        carga.setdefault(roteiro["centro"], [0.0] * HORIZONTE)
        carga[roteiro["centro"]][semana - 1] += horas
    return {c: [arredondar(h) for h in horas] for c, horas in carga.items()}


def analisar_centro(dados, codigo_centro):
    """Linhas do CRP de um centro: semana, carga, uso (%) e sobrecarga."""
    centro = obter_centro(dados, codigo_centro)
    carga = calcular_carga(dados).get(centro["codigo"], [0.0] * HORIZONTE)
    capacidade = centro["capacidade"]
    linhas = []
    for semana, horas in enumerate(carga, start=1):
        linhas.append({
            "semana": semana,
            "carga": horas,
            "capacidade": capacidade,
            "uso": horas / capacidade * 100,
            "sobrecarga": horas > capacidade + 1e-9,
        })
    return linhas


def semanas_em_sobrecarga(dados, codigo_centro):
    """Semanas (1..8) em que a carga supera a capacidade do centro."""
    return [linha["semana"]
            for linha in analisar_centro(dados, codigo_centro)
            if linha["sobrecarga"]]


def _lista_semanas(semanas):
    textos = [str(s) for s in semanas]
    if len(textos) == 1:
        return textos[0]
    return ", ".join(textos[:-1]) + " e " + textos[-1]


def formatar_crp(dados, codigo_centro):
    """Texto do CRP de um centro de trabalho (carga x capacidade)."""
    centro = obter_centro(dados, codigo_centro)
    saida = [f"CARGA x CAPACIDADE - {centro['codigo']} "
             f"{centro['descricao']} "
             f"({formatar_decimal(centro['capacidade'])} h/semana)"]
    linhas = []
    for linha in analisar_centro(dados, centro["codigo"]):
        uso = round(linha["uso"])
        barras = "#" * round(linha["uso"] / 10)
        aviso = "SOBRECARGA" if linha["sobrecarga"] else ""
        linhas.append((linha["semana"], formatar_decimal(linha["carga"]),
                       uso, f"{barras:<12} {aviso}".rstrip()))
    saida.extend(montar_tabela(("Sem", "Carga(h)", "Uso(%)", ""), linhas,
                               ">>><"))
    criticas = semanas_em_sobrecarga(dados, centro["codigo"])
    if criticas:
        artigo = "na semana" if len(criticas) == 1 else "nas semanas"
        saida.append(f"Sugestao: antecipar OPs ou programar hora extra "
                     f"{artigo} {_lista_semanas(criticas)}.")
    else:
        saida.append("Nenhuma semana em sobrecarga.")
    return saida
