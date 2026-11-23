"""Ordens de producao (OP) e de compra (OC) - RF09, RF10 e RF11.

Cada ordem em ``dados["ordens"]`` e um dicionario::

    {"numero": "OP-0011", "tipo": "OP", "item": "PA-001",
     "quantidade": 30.0, "semana_liberacao": 1, "semana_entrega": 2,
     "status": "PLANEJADA", "atrasada": False,
     "data_criacao": "2026-10-02", "data_encerramento": None}

Ciclo de vida: PLANEJADA -> FIRME -> LIBERADA -> ENCERRADA.
A marca ``atrasada`` indica liberacao planejada antes da semana 1 (RN07).
"""

from estoque import registrar_movimento, saldo
from estrutura import componentes_de
from itens import eh_fabricado, obter_item
from utils import (
    HORIZONTE,
    ErroNegocio,
    arredondar,
    formatar_numero,
    hoje_iso,
    montar_tabela,
    validar_data_iso,
    validar_numero,
)

PLANEJADA = "PLANEJADA"
FIRME = "FIRME"
LIBERADA = "LIBERADA"
ENCERRADA = "ENCERRADA"
STATUS_VALIDOS = (PLANEJADA, FIRME, LIBERADA, ENCERRADA)
STATUS_PROGRAMADOS = (FIRME, LIBERADA)


def proximo_numero(dados, tipo):
    """Proximo numero livre para o tipo de ordem (OP-0001, OC-0001...)."""
    maior = 0
    for ordem in dados["ordens"]:
        if ordem["tipo"] == tipo:
            maior = max(maior, int(ordem["numero"].split("-")[1]))
    return f"{tipo}-{maior + 1:04d}"


def criar_ordem(dados, tipo, item, quantidade, semana_liberacao,
                semana_entrega, status=PLANEJADA, data=None):
    """Cria uma ordem de producao (OP) ou de compra (OC)."""
    if tipo not in ("OP", "OC"):
        raise ErroNegocio("tipo de ordem invalido. Use OP ou OC.")
    if status not in STATUS_VALIDOS:
        raise ErroNegocio(f"status '{status}' invalido.")
    registro = obter_item(dados, item)
    if tipo == "OP" and not eh_fabricado(registro):
        raise ErroNegocio(f"{registro['codigo']} e MP: use uma OC.")
    if tipo == "OC" and eh_fabricado(registro):
        raise ErroNegocio(f"{registro['codigo']} e fabricado: use uma OP.")
    validar_numero(quantidade, "A quantidade da ordem", maior_que=0)
    ordem = {
        "numero": proximo_numero(dados, tipo),
        "tipo": tipo,
        "item": registro["codigo"],
        "quantidade": arredondar(quantidade),
        "semana_liberacao": int(semana_liberacao),
        "semana_entrega": int(semana_entrega),
        "status": status,
        "atrasada": int(semana_liberacao) < 1,
        "data_criacao": validar_data_iso(data or hoje_iso()),
        "data_encerramento": None,
    }
    dados["ordens"].append(ordem)
    return ordem


def obter_ordem(dados, numero):
    """Busca uma ordem pelo numero (ex.: OP-0003)."""
    numero = str(numero).strip().upper()
    for ordem in dados["ordens"]:
        if ordem["numero"] == numero:
            return ordem
    raise ErroNegocio(f"ordem {numero} nao encontrada.")


def listar_ordens(dados, status=None, abertas=False):
    """Lista ordens ordenadas (OP antes de OC, por numero).

    `status` filtra por um status; `abertas=True` exclui as encerradas.
    """
    ordens = [o for o in dados["ordens"]
              if (status is None or o["status"] == status)
              and not (abertas and o["status"] == ENCERRADA)]
    return sorted(ordens, key=lambda o: (o["tipo"] != "OP", o["numero"]))


def apagar_planejadas(dados):
    """Remove as ordens PLANEJADAS (RN08). Retorna quantas foram apagadas."""
    antes = len(dados["ordens"])
    dados["ordens"] = [o for o in dados["ordens"]
                       if o["status"] != PLANEJADA]
    return antes - len(dados["ordens"])


def recebimentos_programados(dados, codigo):
    """Recebimentos programados por semana (RN08).

    Considera apenas ordens FIRMES ou LIBERADAS do item. Entregas atrasadas
    (semana < 1) sao tratadas como recebimento na semana 1; entregas alem do
    horizonte sao ignoradas.
    """
    recebimentos = [0.0] * HORIZONTE
    for ordem in dados["ordens"]:
        if (ordem["item"] != codigo
                or ordem["status"] not in STATUS_PROGRAMADOS):
            continue
        semana = max(1, ordem["semana_entrega"])
        if semana <= HORIZONTE:
            recebimentos[semana - 1] += ordem["quantidade"]
    return [arredondar(q) for q in recebimentos]


def producoes_programadas(dados, codigo):
    """OPs FIRMES/LIBERADAS (ainda nao encerradas) de um item fabricado."""
    return [o for o in dados["ordens"]
            if o["tipo"] == "OP" and o["item"] == codigo
            and o["status"] in STATUS_PROGRAMADOS]


def _exigir_status(ordem, esperado, acao, participio):
    """Garante a sequencia PLANEJADA -> FIRME -> LIBERADA -> ENCERRADA."""
    if ordem["status"] != esperado:
        raise ErroNegocio(
            f"nao e possivel {acao} a ordem {ordem['numero']}: status atual "
            f"{ordem['status']}; so ordens {esperado} podem ser "
            f"{participio}.")


def firmar_ordem(dados, numero):
    """PLANEJADA -> FIRME."""
    ordem = obter_ordem(dados, numero)
    _exigir_status(ordem, PLANEJADA, "firmar", "firmadas")
    ordem["status"] = FIRME
    return ordem


def firmar_todas(dados):
    """Firma todas as ordens PLANEJADAS. Retorna quantas foram firmadas."""
    total = 0
    for ordem in dados["ordens"]:
        if ordem["status"] == PLANEJADA:
            ordem["status"] = FIRME
            total += 1
    return total


def liberar_ordem(dados, numero):
    """FIRME -> LIBERADA."""
    ordem = obter_ordem(dados, numero)
    _exigir_status(ordem, FIRME, "liberar", "liberadas")
    ordem["status"] = LIBERADA
    return ordem


def verificar_componentes(dados, ordem):
    """Componentes faltantes para produzir a OP: [(cod, necessario, saldo)]."""
    faltas = []
    for linha in componentes_de(dados, ordem["item"]):
        necessario = arredondar(linha["quantidade"] * ordem["quantidade"])
        disponivel = saldo(dados, linha["componente"])
        if disponivel < necessario:
            faltas.append((linha["componente"], necessario, disponivel))
    return faltas


def apontar_producao(dados, numero, data):
    """Aponta a producao total de uma OP liberada (RF11).

    Baixa os componentes do estoque, da entrada no item produzido e encerra
    a OP. Se faltar qualquer componente, nada e alterado (RN02).
    """
    ordem = obter_ordem(dados, numero)
    if ordem["tipo"] != "OP":
        raise ErroNegocio(
            f"{ordem['numero']} e uma ordem de compra: use 'encerrar' para "
            "registrar o recebimento.")
    if ordem["status"] != LIBERADA:
        raise ErroNegocio(
            f"so e possivel apontar OPs LIBERADAS (a ordem {ordem['numero']} "
            f"esta {ordem['status']}).")

    faltas = verificar_componentes(dados, ordem)
    if faltas:
        detalhes = []
        for codigo, necessario, disponivel in faltas:
            unidade = obter_item(dados, codigo)["unidade"]
            detalhes.append(
                f"  - {codigo}: necessario {formatar_numero(necessario)} "
                f"{unidade}, saldo {formatar_numero(disponivel)} {unidade} "
                f"(faltam {formatar_numero(necessario - disponivel)})")
        raise ErroNegocio(
            f"apontamento rejeitado: faltam componentes para "
            f"{ordem['numero']}.\n" + "\n".join(detalhes))

    documento_consumo = f"{ordem['numero']} ({ordem['item']})"
    for linha in componentes_de(dados, ordem["item"]):
        registrar_movimento(
            dados, linha["componente"], "SAIDA",
            linha["quantidade"] * ordem["quantidade"],
            documento_consumo, data)
    registrar_movimento(
        dados, ordem["item"], "ENTRADA", ordem["quantidade"],
        f"{ordem['numero']} - apontamento de producao", data)
    ordem["status"] = ENCERRADA
    ordem["data_encerramento"] = validar_data_iso(data)
    return ordem


def receber_compra(dados, numero, data):
    """Encerra uma OC liberada: da entrada da materia-prima no estoque."""
    ordem = obter_ordem(dados, numero)
    if ordem["tipo"] != "OC":
        raise ErroNegocio(f"{ordem['numero']} e uma OP: use o apontamento.")
    if ordem["status"] != LIBERADA:
        raise ErroNegocio(
            f"so e possivel encerrar OCs LIBERADAS (a ordem "
            f"{ordem['numero']} esta {ordem['status']}).")
    registrar_movimento(
        dados, ordem["item"], "ENTRADA", ordem["quantidade"],
        f"{ordem['numero']} - recebimento de compra", data)
    ordem["status"] = ENCERRADA
    ordem["data_encerramento"] = validar_data_iso(data)
    return ordem


def encerrar_ordem(dados, numero, data):
    """Encerra uma ordem liberada (OP: apontamento; OC: recebimento)."""
    ordem = obter_ordem(dados, numero)
    if ordem["tipo"] == "OP":
        return apontar_producao(dados, numero, data)
    return receber_compra(dados, numero, data)


def status_exibicao(ordem):
    """Status mostrado na tela (RN07).

    Ordens planejadas com liberacao antes da semana 1 aparecem como
    ATRASADA; se forem firmadas, a marca continua visivel ate a liberacao.
    """
    if ordem["atrasada"] and ordem["status"] == PLANEJADA:
        return "ATRASADA"
    if ordem["atrasada"] and ordem["status"] == FIRME:
        return "FIRME (atrasada)"
    return ordem["status"]


def formatar_ordens(ordens):
    """Tabela de texto para uma lista de ordens."""
    if not ordens:
        return ["Nenhuma ordem encontrada."]
    linhas = [
        (o["numero"], o["tipo"], o["item"], formatar_numero(o["quantidade"]),
         f"S{o['semana_liberacao']}", f"S{o['semana_entrega']}",
         status_exibicao(o))
        for o in ordens
    ]
    cabecalho = ("Ordem", "Tipo", "Item", "Qtde", "Liberar", "Entregar",
                 "Status")
    return montar_tabela(cabecalho, linhas, "<<<>>><")
