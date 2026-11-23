"""Gestao de estoque: movimentacoes, saldo e kardex (RF04, RF05).

* ``dados["estoque"]``   -> ``{codigo: saldo}``
* ``dados["movimentos"]`` -> lista de dicionarios (kardex de todos os itens)::

    {"id": 1, "data": "2026-10-01", "codigo": "MP-202", "tipo": "ENTRADA",
     "quantidade": 60.0, "saldo": 60.0, "documento": "NF 4521 - ..."}

A ``quantidade`` e sempre o efeito sobre o saldo (negativa nas saidas).
Nao existe funcao para excluir ou editar movimentos (RN10): correcoes sao
feitas por meio de AJUSTE.
"""

from itens import listar_itens, obter_item
from utils import (
    ErroNegocio,
    arredondar,
    formatar_data,
    formatar_moeda,
    formatar_numero,
    formatar_quantidade_sinal,
    montar_tabela,
    validar_data_iso,
    validar_numero,
)

TIPOS_MOVIMENTO = ("ENTRADA", "SAIDA", "AJUSTE")


def saldo(dados, codigo):
    """Saldo atual de um item."""
    return dados["estoque"].get(codigo, 0.0)


def calcular_variacao(dados, codigo, tipo, quantidade):
    """Valida a movimentacao (sem alterar nada) e devolve a variacao.

    Aplica RN02: o saldo nunca pode ficar negativo.
    """
    item = obter_item(dados, codigo)
    tipo = str(tipo).strip().upper()
    if tipo not in TIPOS_MOVIMENTO:
        raise ErroNegocio(
            "tipo de movimentacao invalido. Use "
            f"{', '.join(TIPOS_MOVIMENTO)}.")
    atual = saldo(dados, item["codigo"])
    unidade = item["unidade"]

    if tipo == "AJUSTE":
        if quantidade == 0:
            raise ErroNegocio("o ajuste deve ser diferente de zero.")
        variacao = quantidade
    else:
        validar_numero(quantidade, "A quantidade", maior_que=0)
        variacao = quantidade if tipo == "ENTRADA" else -quantidade

    if arredondar(atual + variacao) < 0:
        if tipo == "AJUSTE":
            raise ErroNegocio(
                "o ajuste deixaria o saldo negativo "
                f"(saldo atual: {formatar_numero(atual)} {unidade}). "
                "Operacao cancelada.")
        raise ErroNegocio(
            f"saldo insuficiente (saldo atual: {formatar_numero(atual)} "
            f"{unidade}). Operacao cancelada.")
    return variacao


def registrar_movimento(dados, codigo, tipo, quantidade, documento, data):
    """Registra uma movimentacao e atualiza o saldo (RF04).

    `data` deve estar no formato ISO (aaaa-mm-dd).
    """
    item = obter_item(dados, codigo)
    codigo = item["codigo"]
    tipo = str(tipo).strip().upper()
    documento = str(documento).strip()
    if not documento:
        raise ErroNegocio(
            "informe o documento/motivo da movimentacao (RN10).")
    data = validar_data_iso(data)
    variacao = calcular_variacao(dados, codigo, tipo, quantidade)

    novo_saldo = arredondar(saldo(dados, codigo) + variacao)
    dados["estoque"][codigo] = novo_saldo
    proximo_id = max((m["id"] for m in dados["movimentos"]), default=0) + 1
    movimento = {
        "id": proximo_id,
        "data": data,
        "codigo": codigo,
        "tipo": tipo,
        "quantidade": arredondar(variacao),
        "saldo": novo_saldo,
        "documento": documento,
    }
    dados["movimentos"].append(movimento)
    return movimento


def alerta_seguranca(dados, codigo):
    """Mensagem de alerta se o saldo estiver abaixo do estoque de seguranca."""
    item = obter_item(dados, codigo)
    atual = saldo(dados, item["codigo"])
    minimo = item["estoque_seguranca"]
    if atual < minimo:
        unidade = item["unidade"]
        return (f"ALERTA: saldo ({formatar_numero(atual)} {unidade}) abaixo "
                f"do estoque de seguranca ({formatar_numero(minimo)} "
                f"{unidade}).")
    return None


def obter_kardex(dados, codigo):
    """Movimentos de um item, na ordem de registro."""
    item = obter_item(dados, codigo)
    return [m for m in dados["movimentos"] if m["codigo"] == item["codigo"]]


def formatar_kardex(dados, codigo):
    """Texto do kardex de um item, com alerta de estoque de seguranca."""
    item = obter_item(dados, codigo)
    saida = [f"KARDEX - {item['codigo']} {item['descricao']} "
             f"({item['unidade']})"]
    movimentos = obter_kardex(dados, codigo)
    if not movimentos:
        saida.append("(nenhuma movimentacao registrada)")
    else:
        linhas = [
            (formatar_data(m["data"]), m["tipo"],
             formatar_quantidade_sinal(m["quantidade"]),
             formatar_numero(m["saldo"]), m["documento"])
            for m in movimentos
        ]
        saida.extend(montar_tabela(
            ("Data", "Tipo", "Qtde", "Saldo", "Documento"), linhas, "<<>><"))
    alerta = alerta_seguranca(dados, codigo)
    saida.append("")
    saida.append(alerta if alerta else "Saldo dentro do estoque de seguranca.")
    return saida


def posicao_estoque(dados):
    """Linhas (dicionarios) com a posicao de estoque de todos os itens."""
    linhas = []
    for item in listar_itens(dados):
        atual = saldo(dados, item["codigo"])
        linhas.append({
            "codigo": item["codigo"],
            "descricao": item["descricao"],
            "tipo": item["tipo"],
            "unidade": item["unidade"],
            "saldo": atual,
            "estoque_seguranca": item["estoque_seguranca"],
            "situacao": ("ABAIXO DO ES" if atual < item["estoque_seguranca"]
                         else "OK"),
            "custo_unitario": item["custo_unitario"],
            "valor": round(atual * item["custo_unitario"], 2),
        })
    return linhas


def formatar_posicao(dados):
    """Tabela de texto com a posicao de estoque."""
    linhas = [
        (p["codigo"], p["descricao"], p["unidade"],
         formatar_numero(p["saldo"]), formatar_numero(p["estoque_seguranca"]),
         formatar_moeda(p["valor"]), p["situacao"])
        for p in posicao_estoque(dados)
    ]
    cabecalho = ("Codigo", "Descricao", "Un", "Saldo", "Est.Seg.",
                 "Valor (R$)", "Situacao")
    return montar_tabela(cabecalho, linhas, "<<<>>><")
