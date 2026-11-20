import csv
import os
from persistencia import carregar_json

PASTA_RELATORIOS = "docs"


def exportar_posicao_estoque_csv() -> str:
    os.makedirs(PASTA_RELATORIOS, exist_ok=True)
    itens = carregar_json("itens")
    estoque = carregar_json("estoque")

    caminho = os.path.join(PASTA_RELATORIOS, "posicao_estoque.csv")
    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(
            [
                "codigo",
                "tipo",
                "descricao",
                "unidade",
                "saldo_atual",
                "estoque_seguranca",
                "custo_unitario",
                "valor_total_estoque",
                "status",
            ]
        )
        for cod in sorted(itens.keys()):
            item = itens[cod]
            saldo = float(estoque.get(cod, 0.0))
            es = float(item["estoque_seguranca"])
            custo = float(item["custo_unitario"])
            valor_total = round(saldo * custo, 2)
            status = "ABAIXO_ES" if saldo < es else "OK"
            escritor.writerow(
                [
                    cod,
                    item["tipo"],
                    item["descricao"],
                    item["unidade"],
                    saldo,
                    es,
                    custo,
                    valor_total,
                    status,
                ]
            )
    return caminho


def exportar_lista_ordens_csv() -> str:
    os.makedirs(PASTA_RELATORIOS, exist_ok=True)
    ordens = carregar_json("ordens", padrao=[])
    itens = carregar_json("itens")

    caminho = os.path.join(PASTA_RELATORIOS, "lista_ordens.csv")
    with open(caminho, "w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(
            [
                "numero",
                "tipo",
                "item",
                "descricao_item",
                "quantidade",
                "semana_liberacao",
                "semana_entrega",
                "status",
            ]
        )
        for ordem in ordens:
            desc = itens.get(ordem["item"], {}).get("descricao", "")
            escritor.writerow(
                [
                    ordem["numero"],
                    ordem["tipo"],
                    ordem["item"],
                    desc,
                    ordem["quantidade"],
                    ordem["semana_liberacao"],
                    ordem["semana_entrega"],
                    ordem["status"],
                ]
            )
    return caminho


def exportar_todos_relatorios() -> None:
    arq_estoque = exportar_posicao_estoque_csv()
    arq_ordens = exportar_lista_ordens_csv()
    print("\nRelatórios exportados com sucesso:")
    print(f"  - Posição de Estoque: {arq_estoque}")
    print(f"  - Lista de Ordens:    {arq_ordens}")