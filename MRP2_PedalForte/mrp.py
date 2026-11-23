"""Calculo MRP (RF08, RF09, RN04 a RN08).

O MRP processa os itens por tipo - primeiro os PA, depois os SA e por fim as
MP (RN04) - de modo que, ao calcular um componente, as liberacoes planejadas
de todos os seus pais ja estejam disponiveis.

Resultado guardado em ``dados["mrp"]``::

    {"executado_em": "2026-10-02",
     "registros": {codigo: {"estoque_inicial": 40.0,
                            "nb": [...], "rp": [...], "ep": [...],
                            "nl": [...], "rpl": [...], "lib": [...]}},
     "mensagens": ["..."]}

Todas as listas possuem ``HORIZONTE`` (8) posicoes, uma por semana.
"""

import estrutura
import mps
import ordens
from estoque import saldo
from itens import listar_itens, obter_item
from utils import (
    HORIZONTE,
    ErroNegocio,
    arredondar,
    formatar_data,
    formatar_numero,
    hoje_iso,
    montar_tabela,
)

ORDEM_DE_PROCESSAMENTO = ("PA", "SA", "MP")  # RN04


def _zeros():
    return [0.0] * HORIZONTE


def calcular_registro(item, necessidade_bruta, recebimentos, estoque_inicial):
    """Calcula o registro MRP de um item (RN05, RN06 e RN07).

    Parametros:
        item: dicionario do item (lead time, estoque de seguranca, lote).
        necessidade_bruta: lista de HORIZONTE valores (NB).
        recebimentos: lista de HORIZONTE valores (RP, recebimentos
            programados de ordens firmes/liberadas).
        estoque_inicial: saldo fisico atual (EP da semana 0).

    Retorna ``(registro, planejadas)`` onde ``planejadas`` e a lista de
    tuplas ``(semana_entrega, semana_liberacao, quantidade)``; liberacoes
    com semana < 1 correspondem a ordens atrasadas (RN07).
    """
    seguranca = item["estoque_seguranca"]
    lote_minimo = item["lote_minimo"]
    lead_time = item["lead_time"]

    registro = {"estoque_inicial": arredondar(estoque_inicial), "nb": [],
                "rp": [], "ep": [], "nl": [], "rpl": [], "lib": _zeros()}
    planejadas = []
    ep_anterior = estoque_inicial

    for semana in range(1, HORIZONTE + 1):
        nb = necessidade_bruta[semana - 1]
        rp = recebimentos[semana - 1]
        # RN05: NL(t) = max(0, NB(t) + ES - (EP(t-1) + RP(t)))
        nl = arredondar(max(0.0, nb + seguranca - (ep_anterior + rp)))
        # RN06: recebimento planejado = max(NL, lote minimo)
        rpl = arredondar(max(nl, lote_minimo)) if nl > 0 else 0.0
        ep = arredondar(ep_anterior + rp + rpl - nb)

        registro["nb"].append(arredondar(nb))
        registro["rp"].append(arredondar(rp))
        registro["ep"].append(ep)
        registro["nl"].append(nl)
        registro["rpl"].append(rpl)

        if rpl > 0:
            # RN07: liberacao = semana do recebimento - lead time
            semana_liberacao = semana - lead_time
            planejadas.append((semana, semana_liberacao, rpl))
            if semana_liberacao >= 1:
                registro["lib"][semana_liberacao - 1] = arredondar(
                    registro["lib"][semana_liberacao - 1] + rpl)
        ep_anterior = ep
    return registro, planejadas


def _demanda_dependente(dados, codigo, liberacoes, mapa):
    """Necessidade bruta de um componente a partir de seus pais (RN04).

    Para cada pai: liberacoes planejadas x quantidade por unidade. Alem
    disso, OPs FIRMES/LIBERADAS do pai ainda nao apontadas reservam os
    componentes na semana de liberacao (ou na semana 1, se ja passou),
    pois o consumo fisico so ocorre no apontamento (RF11).
    """
    nb = _zeros()
    for pai, quantidade in mapa.get(codigo, []):
        for indice, liberado in enumerate(liberacoes.get(pai, _zeros())):
            nb[indice] += liberado * quantidade
        for ordem in ordens.producoes_programadas(dados, pai):
            semana = max(1, ordem["semana_liberacao"])
            if semana <= HORIZONTE:
                nb[semana - 1] += ordem["quantidade"] * quantidade
    return [arredondar(valor) for valor in nb]


def executar_mrp(dados, data_execucao=None):
    """Executa o MRP para todos os itens e gera as ordens planejadas.

    1. Apaga as ordens PLANEJADAS anteriores (RN08).
    2. Processa PA, SA e MP, nessa ordem (RN04).
    3. Gera OPs (itens fabricados) e OCs (materias-primas) com semanas de
       liberacao e entrega (RF09), marcando as atrasadas (RN07).

    Retorna um dicionario-resumo com as mensagens de excecao e as ordens
    criadas.
    """
    data_execucao = data_execucao or hoje_iso()
    apagadas = ordens.apagar_planejadas(dados)
    mapa = estrutura.mapa_pais(dados)
    liberacoes = {}
    registros = {}
    criadas = []
    mensagens = []

    for tipo in ORDEM_DE_PROCESSAMENTO:
        for item in listar_itens(dados, tipo):
            codigo = item["codigo"]
            if tipo == "PA":
                necessidade = mps.obter_plano(dados, codigo)
            else:
                necessidade = _demanda_dependente(dados, codigo, liberacoes,
                                                  mapa)
            registro, planejadas = calcular_registro(
                item, necessidade,
                ordens.recebimentos_programados(dados, codigo),
                saldo(dados, codigo))
            registros[codigo] = registro
            liberacoes[codigo] = registro["lib"]

            tipo_ordem = "OC" if tipo == "MP" else "OP"
            for entrega, liberacao, quantidade in planejadas:
                ordem = ordens.criar_ordem(
                    dados, tipo_ordem, codigo, quantidade, liberacao,
                    entrega, data=data_execucao)
                criadas.append(ordem)
                if ordem["atrasada"]:
                    mensagens.append(
                        f"{ordem['numero']} ({codigo}): liberacao planejada "
                        f"para a semana {liberacao}, antes da semana 1; "
                        f"entrega na semana {entrega}. Ordem ATRASADA.")

    dados["mrp"] = {"executado_em": data_execucao, "registros": registros,
                    "mensagens": mensagens}
    return {"apagadas": apagadas, "criadas": criadas, "mensagens": mensagens}


def mrp_executado(dados):
    """Indica se existe um resultado de MRP calculado."""
    return bool(dados.get("mrp", {}).get("registros"))


def obter_registro(dados, codigo):
    """Registro MRP de um item (exige MRP ja executado)."""
    item = obter_item(dados, codigo)
    if not mrp_executado(dados):
        raise ErroNegocio("o MRP ainda nao foi executado. Execute-o antes de "
                          "consultar um registro.")
    registro = dados["mrp"]["registros"].get(item["codigo"])
    if registro is None:
        raise ErroNegocio(
            f"{item['codigo']} nao consta na ultima execucao do MRP "
            "(item cadastrado depois). Execute o MRP novamente.")
    return registro


def formatar_registro(dados, codigo):
    """Texto do registro MRP de um item (mockup 6.4)."""
    item = obter_item(dados, codigo)
    registro = obter_registro(dados, codigo)
    saida = [
        f"REGISTRO MRP - {item['codigo']} {item['descricao']}",
        f"Lead time: {item['lead_time']} sem | "
        f"Est. seguranca: {formatar_numero(item['estoque_seguranca'])} | "
        f"Lote min.: {formatar_numero(item['lote_minimo'])} | "
        f"Estoque: {formatar_numero(registro['estoque_inicial'])}",
        f"(MRP executado em {formatar_data(dados['mrp']['executado_em'])})",
        "",
    ]
    cabecalho = ["Semana"] + [str(s) for s in range(1, HORIZONTE + 1)]
    rotulos = (
        ("Necessidade bruta", "nb"),
        ("Receb. programados", "rp"),
        ("Estoque projetado", "ep"),
        ("Necessidade liquida", "nl"),
        ("Receb. planejados", "rpl"),
        ("Liberacao planejada", "lib"),
    )
    linhas = [[rotulo] + [formatar_numero(v) for v in registro[chave]]
              for rotulo, chave in rotulos]
    saida.extend(montar_tabela(cabecalho, linhas, "<" + ">" * HORIZONTE))
    return saida


def formatar_resumo(resumo, data_execucao):
    """Texto de ordens planejadas e mensagens de excecao (mockup 6.5)."""
    saida = [f"ORDENS PLANEJADAS - execucao do MRP em "
             f"{formatar_data(data_execucao)}"]
    saida.extend(ordens.formatar_ordens(resumo["criadas"]))
    saida.append("")
    quantidade = len(resumo["mensagens"])
    if quantidade:
        rotulo = "mensagem" if quantidade == 1 else "mensagens"
        saida.append(f"{quantidade} {rotulo} de excecao: ordens com "
                     "liberacao antes da semana 1.")
        saida.extend(f"  ! {mensagem}" for mensagem in resumo["mensagens"])
    else:
        saida.append("Nenhuma mensagem de excecao.")
    return saida
