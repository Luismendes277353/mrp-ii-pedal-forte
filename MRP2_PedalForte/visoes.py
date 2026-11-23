"""Dados prontos para exibicao em tabelas (usados pela interface grafica).

Todas as funcoes aqui sao puras: recebem o dicionario de dados e devolvem
listas de linhas de texto, sem depender do Tkinter. Assim a logica de
apresentacao da interface grafica pode ser testada sem abrir janelas.

Convencao: as funcoes ``linhas_*`` devolvem uma lista de tuplas
``(valores, tag)``; a ``tag`` (ou ``None``) escolhe a cor da linha.
"""

import capacidade
import custos
import estoque
import estrutura
import mps
import mrp
import ordens
from itens import eh_fabricado, listar_itens, obter_item
from utils import (
    HORIZONTE,
    formatar_data,
    formatar_decimal,
    formatar_moeda,
    formatar_numero,
    formatar_quantidade_sinal,
)


def rotulo_item(item):
    """Texto de um item para caixas de selecao."""
    return f"{item['codigo']} - {item['descricao']}"


def rotulos_itens(dados, tipos=None):
    """Rotulos dos itens (opcionalmente filtrados por tipos)."""
    return [rotulo_item(item) for item in listar_itens(dados)
            if tipos is None or item["tipo"] in tipos]


def rotulos_centros(dados):
    """Rotulos dos centros de trabalho."""
    return [f"{c['codigo']} - {c['descricao']}"
            for c in sorted(dados["centros"].values(),
                            key=lambda c: c["codigo"])]


def codigo_do_rotulo(rotulo):
    """Extrai o codigo de um rotulo 'CODIGO - descricao'."""
    return str(rotulo).split(" ")[0].strip()


def linhas_itens(dados, tipo=None):
    """Itens cadastrados."""
    return [((i["codigo"], i["descricao"], i["tipo"], i["unidade"],
              formatar_moeda(i["custo_unitario"]), i["lead_time"],
              formatar_numero(i["estoque_seguranca"]),
              formatar_numero(i["lote_minimo"])), None)
            for i in listar_itens(dados, tipo)]


def linhas_posicao(dados):
    """Posicao de estoque; itens abaixo do estoque de seguranca em alerta."""
    return [((p["codigo"], p["descricao"], p["unidade"],
              formatar_numero(p["saldo"]),
              formatar_numero(p["estoque_seguranca"]),
              formatar_moeda(p["valor"]), p["situacao"]),
             "alerta" if p["situacao"] != "OK" else None)
            for p in estoque.posicao_estoque(dados)]


def linhas_kardex(dados, codigo):
    """Kardex de um item."""
    return [((formatar_data(m["data"]), m["tipo"],
              formatar_quantidade_sinal(m["quantidade"]),
              formatar_numero(m["saldo"]), m["documento"]), None)
            for m in estoque.obter_kardex(dados, codigo)]


def linhas_mps(dados):
    """MPS: uma linha por produto acabado, com as 8 semanas e o total."""
    linhas = []
    for item in listar_itens(dados, "PA"):
        plano = mps.obter_plano(dados, item["codigo"])
        valores = (item["codigo"], item["descricao"],
                   *(formatar_numero(q) for q in plano),
                   formatar_numero(sum(plano)))
        linhas.append((valores, None))
    return linhas


def linhas_registro_mrp(dados, codigo):
    """Registro MRP de um item (uma linha por indicador)."""
    registro = mrp.obter_registro(dados, codigo)
    rotulos = (("Necessidade bruta", "nb"), ("Receb. programados", "rp"),
               ("Estoque projetado", "ep"), ("Necessidade liquida", "nl"),
               ("Receb. planejados", "rpl"), ("Liberacao planejada", "lib"))
    return [((rotulo, *(formatar_numero(v) for v in registro[chave])), None)
            for rotulo, chave in rotulos]


def descricao_registro_mrp(dados, codigo):
    """Linha de cabecalho do registro MRP (lead time, ES, lote, estoque)."""
    item = obter_item(dados, codigo)
    registro = mrp.obter_registro(dados, codigo)
    return (f"{item['codigo']} {item['descricao']}  |  Lead time: "
            f"{item['lead_time']} sem  |  Est. seguranca: "
            f"{formatar_numero(item['estoque_seguranca'])}  |  Lote min.: "
            f"{formatar_numero(item['lote_minimo'])}  |  Estoque inicial: "
            f"{formatar_numero(registro['estoque_inicial'])}")


def tag_da_ordem(ordem):
    """Cor da linha de uma ordem na tabela."""
    if ordem["atrasada"] and ordem["status"] in (ordens.PLANEJADA,
                                                 ordens.FIRME):
        return "atrasada"
    return ordem["status"].lower()


def linhas_ordens(dados, mostrar_encerradas=False):
    """Ordens de producao e de compra."""
    lista = ordens.listar_ordens(dados, abertas=not mostrar_encerradas)
    linhas = []
    for ordem in lista:
        item = obter_item(dados, ordem["item"])
        valores = (ordem["numero"], ordem["tipo"], item["codigo"],
                   item["descricao"], formatar_numero(ordem["quantidade"]),
                   item["unidade"], f"S{ordem['semana_liberacao']}",
                   f"S{ordem['semana_entrega']}",
                   ordens.status_exibicao(ordem))
        linhas.append((valores, tag_da_ordem(ordem)))
    return linhas


def linhas_crp(dados, codigo_centro):
    """Carga x capacidade de um centro, semana a semana."""
    linhas = []
    for linha in capacidade.analisar_centro(dados, codigo_centro):
        valores = (linha["semana"], formatar_decimal(linha["carga"]),
                   formatar_decimal(linha["capacidade"]),
                   round(linha["uso"]),
                   "SOBRECARGA" if linha["sobrecarga"] else "OK")
        linhas.append((valores, "alerta" if linha["sobrecarga"] else None))
    return linhas


def sugestao_crp(dados, codigo_centro):
    """Texto de sugestao do CRP (ultima linha de ``formatar_crp``)."""
    return capacidade.formatar_crp(dados, codigo_centro)[-1]


def linhas_custos(dados):
    """Custo padrao x custo cadastrado dos itens fabricados."""
    linhas = []
    for item in listar_itens(dados):
        if eh_fabricado(item):
            linhas.append(((item["codigo"], item["descricao"],
                            formatar_moeda(
                                custos.custo_padrao(dados, item["codigo"])),
                            formatar_moeda(item["custo_unitario"])), None))
    return linhas


def linhas_bom(dados, codigo):
    """Explosao da BOM: tuplas ``(nivel, codigo, descricao, qtde, un)``."""
    raiz = obter_item(dados, codigo)
    linhas = [(0, raiz["codigo"], raiz["descricao"], "", raiz["unidade"])]
    for nivel, _, componente, quantidade in estrutura.montar_arvore(
            dados, raiz["codigo"]):
        item = obter_item(dados, componente)
        linhas.append((nivel, item["codigo"], item["descricao"],
                       formatar_numero(quantidade), item["unidade"]))
    return linhas


def texto_roteiro_e_custo(dados, codigo):
    """Resumo de roteiro e custo padrao de um item fabricado."""
    roteiro = capacidade.obter_roteiro(dados, codigo)
    if roteiro:
        texto = (f"Roteiro: {roteiro['centro']}, "
                 f"{formatar_numero(roteiro['tempo_unitario'])} h/un")
    else:
        texto = "Roteiro: nao definido"
    custo = custos.custo_padrao(dados, codigo)
    return f"{texto}  |  Custo padrao: R$ {formatar_moeda(custo)}"


def linhas_modelos(resultado):
    """Desempenho dos modelos de previsao no conjunto de teste."""
    return [((a["rotulo"], formatar_numero(a["mae"], 2),
              formatar_numero(a["rmse"], 2),
              "escolhido" if a["modelo"] == resultado["modelo"] else ""),
             "escolhido" if a["modelo"] == resultado["modelo"] else None)
            for a in resultado["avaliacao"]]


def linhas_previsao(resultado):
    """Previsao e faixa de ~80% das 8 semanas."""
    return [
        (("Previsao", *resultado["previsao"]), "escolhido"),
        (("Faixa minima", *resultado["faixa_inferior"]), None),
        (("Faixa maxima", *resultado["faixa_superior"]), None),
    ]


def descricao_modelo(resultado):
    """Resumo do modelo escolhido e do seu erro."""
    parametros = ", ".join(f"{k}={formatar_numero(v)}"
                           for k, v in resultado["parametros"].items())
    texto = f"Modelo escolhido: {resultado['rotulo']}"
    if parametros:
        texto += f" ({parametros})"
    return (f"{texto}  |  MAE no teste: "
            f"{formatar_numero(resultado['erro_mae'], 2)} un/semana  |  "
            f"historico: {len(resultado['historico'])} semanas")


def resumo_painel(dados):
    """Indicadores gerais exibidos na aba Painel."""
    posicao = estoque.posicao_estoque(dados)
    abertas = ordens.listar_ordens(dados, abertas=True)
    atrasadas = [o for o in abertas if o["atrasada"]
                 and o["status"] in (ordens.PLANEJADA, ordens.FIRME)]
    sobrecarga = {}
    for codigo in sorted(dados["centros"]):
        semanas = capacidade.semanas_em_sobrecarga(dados, codigo)
        if semanas:
            sobrecarga[codigo] = semanas
    executado = dados.get("mrp", {}).get("executado_em")
    return {
        "itens": len(dados["itens"]),
        "abaixo_seguranca": [p for p in posicao if p["situacao"] != "OK"],
        "ordens_abertas": len(abertas),
        "ordens_atrasadas": len(atrasadas),
        "centros_sobrecarga": sobrecarga,
        "valor_estoque": sum(p["valor"] for p in posicao),
        "mrp_executado_em": formatar_data(executado) if executado
        else "nunca",
        "mensagens": list(dados.get("mrp", {}).get("mensagens", [])),
    }


def colunas_semanas():
    """Titulos das colunas de semana (S1 a S8)."""
    return [f"S{semana}" for semana in range(1, HORIZONTE + 1)]
