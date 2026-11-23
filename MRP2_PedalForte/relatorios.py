"""Exportacao de relatorios em CSV (RF14).

Os arquivos usam ponto e virgula como separador, virgula decimal e
codificacao UTF-8 com BOM, para abrirem corretamente no Excel/LibreOffice
em portugues.
"""

import csv
from pathlib import Path

import estoque
import ordens
from itens import obter_item
from persistencia import PASTA_SAIDA
from utils import ErroNegocio, formatar_data, formatar_numero


def _gravar_csv(caminho, cabecalho, linhas):
    caminho = Path(caminho)
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
            escritor = csv.writer(arquivo, delimiter=";")
            escritor.writerow(cabecalho)
            escritor.writerows(linhas)
    except OSError as erro:
        raise ErroNegocio(
            f"nao foi possivel gravar {caminho.name}: {erro}") from erro
    return caminho


def exportar_posicao_estoque(dados, pasta=PASTA_SAIDA):
    """Exporta a posicao de estoque de todos os itens."""
    cabecalho = ("codigo", "descricao", "tipo", "unidade", "saldo",
                 "estoque_seguranca", "situacao", "custo_unitario",
                 "valor_em_estoque")
    linhas = []
    for posicao in estoque.posicao_estoque(dados):
        linhas.append((
            posicao["codigo"], posicao["descricao"], posicao["tipo"],
            posicao["unidade"], formatar_numero(posicao["saldo"]),
            formatar_numero(posicao["estoque_seguranca"]),
            posicao["situacao"],
            formatar_numero(posicao["custo_unitario"], 2),
            formatar_numero(posicao["valor"], 2)))
    return _gravar_csv(Path(pasta) / "posicao_estoque.csv", cabecalho,
                       linhas)


def exportar_ordens(dados, pasta=PASTA_SAIDA):
    """Exporta a lista de ordens (OP e OC) com todos os status."""
    cabecalho = ("ordem", "tipo", "item", "descricao", "quantidade",
                 "unidade", "semana_liberacao", "semana_entrega", "status",
                 "data_criacao", "data_encerramento")
    linhas = []
    for ordem in ordens.listar_ordens(dados):
        item = obter_item(dados, ordem["item"])
        linhas.append((
            ordem["numero"], ordem["tipo"], ordem["item"],
            item["descricao"], formatar_numero(ordem["quantidade"]),
            item["unidade"], ordem["semana_liberacao"],
            ordem["semana_entrega"], ordens.status_exibicao(ordem),
            formatar_data(ordem["data_criacao"]),
            formatar_data(ordem["data_encerramento"])))
    return _gravar_csv(Path(pasta) / "ordens.csv", cabecalho, linhas)
