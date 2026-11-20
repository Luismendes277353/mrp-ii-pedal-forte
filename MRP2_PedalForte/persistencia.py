import csv
import json
import os
from typing import Any

PASTA_DATA = "data"

ARQUIVOS_JSON = {
    "itens": os.path.join(PASTA_DATA, "itens.json"),
    "estrutura": os.path.join(PASTA_DATA, "estrutura.json"),
    "estoque": os.path.join(PASTA_DATA, "estoque.json"),
    "centros": os.path.join(PASTA_DATA, "centros.json"),
    "roteiros": os.path.join(PASTA_DATA, "roteiros.json"),
    "mps": os.path.join(PASTA_DATA, "mps.json"),
    "ordens": os.path.join(PASTA_DATA, "ordens.json"),
}

ARQUIVO_MOVIMENTOS = os.path.join(PASTA_DATA, "movimentos.csv")


def salvar_json(chave: str, dados: Any) -> None:
    os.makedirs(PASTA_DATA, exist_ok=True)
    caminho = ARQUIVOS_JSON[chave]
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=4, ensure_ascii=False)


def carregar_json(chave: str, padrao: Any = None) -> Any:
    caminho = ARQUIVOS_JSON[chave]
    if not os.path.exists(caminho):
        return {} if padrao is None else padrao
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def registrar_movimento_csv(
    data: str,
    codigo: str,
    tipo: str,
    quantidade: float,
    saldo_apos: float,
    documento: str,
) -> None:
    os.makedirs(PASTA_DATA, exist_ok=True)
    arquivo_existe = os.path.exists(ARQUIVO_MOVIMENTOS)
    with open(ARQUIVO_MOVIMENTOS, "a", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        if not arquivo_existe:
            escritor.writerow(
                ["data", "codigo", "tipo", "quantidade", "saldo_apos", "documento"]
            )
        escritor.writerow([data, codigo, tipo, quantidade, saldo_apos, documento])


def carregar_movimentos_csv() -> list[dict[str, str]]:
    if not os.path.exists(ARQUIVO_MOVIMENTOS):
        return []
    with open(ARQUIVO_MOVIMENTOS, "r", encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo, delimiter=";")
        return list(leitor)


def inicializar_base_demonstracao() -> None:
    os.makedirs(PASTA_DATA, exist_ok=True)
    if os.path.exists(ARQUIVOS_JSON["itens"]):
        return

    itens_demo = {
        "PA-001": {
            "descricao": "Bicicleta Aro 29 MTB",
            "tipo": "PA",
            "unidade": "un",
            "custo_unitario": 0.0,
            "lead_time": 1,
            "estoque_seguranca": 5,
            "lote_minimo": 10,
        },
        "PA-002": {
            "descricao": "Bicicleta Urbana Aro 26",
            "tipo": "PA",
            "unidade": "un",
            "custo_unitario": 0.0,
            "lead_time": 1,
            "estoque_seguranca": 4,
            "lote_minimo": 8,
        },
        "SA-010": {
            "descricao": "Quadro aro 29 soldado",
            "tipo": "SA",
            "unidade": "un",
            "custo_unitario": 0.0,
            "lead_time": 1,
            "estoque_seguranca": 8,
            "lote_minimo": 15,
        },
        "SA-020": {
            "descricao": "Roda aro 29 montada",
            "tipo": "SA",
            "unidade": "un",
            "custo_unitario": 0.0,
            "lead_time": 1,
            "estoque_seguranca": 10,
            "lote_minimo": 80,
        },
        "MP-100": {
            "descricao": "Tubo de aco carbono",
            "tipo": "MP",
            "unidade": "m",
            "custo_unitario": 32.00,
            "lead_time": 2,
            "estoque_seguranca": 30,
            "lote_minimo": 100,
        },
        "MP-101": {
            "descricao": "Tinta epoxi",
            "tipo": "MP",
            "unidade": "L",
            "custo_unitario": 34.00,
            "lead_time": 1,
            "estoque_seguranca": 10,
            "lote_minimo": 20,
        },
        "MP-200": {
            "descricao": "Aro 29 aluminio",
            "tipo": "MP",
            "unidade": "un",
            "custo_unitario": 55.00,
            "lead_time": 2,
            "estoque_seguranca": 20,
            "lote_minimo": 50,
        },
        "MP-201": {
            "descricao": "Raio inox",
            "tipo": "MP",
            "unidade": "un",
            "custo_unitario": 0.80,
            "lead_time": 2,
            "estoque_seguranca": 500,
            "lote_minimo": 2000,
        },
        "MP-202": {
            "descricao": "Pneu 29 x 2.20",
            "tipo": "MP",
            "unidade": "un",
            "custo_unitario": 48.00,
            "lead_time": 1,
            "estoque_seguranca": 20,
            "lote_minimo": 40,
        },
        "MP-300": {
            "descricao": "Guidao",
            "tipo": "MP",
            "unidade": "un",
            "custo_unitario": 45.00,
            "lead_time": 1,
            "estoque_seguranca": 15,
            "lote_minimo": 30,
        },
        "MP-301": {
            "descricao": "Kit transmissao 12v",
            "tipo": "MP",
            "unidade": "un",
            "custo_unitario": 320.00,
            "lead_time": 2,
            "estoque_seguranca": 10,
            "lote_minimo": 20,
        },
        "MP-302": {
            "descricao": "Selim ergonomico",
            "tipo": "MP",
            "unidade": "un",
            "custo_unitario": 38.00,
            "lead_time": 1,
            "estoque_seguranca": 15,
            "lote_minimo": 25,
        },
    }

    estrutura_demo = {
        "PA-001": [
            {"componente": "SA-010", "quantidade": 1.0},
            {"componente": "SA-020", "quantidade": 2.0},
            {"componente": "MP-300", "quantidade": 1.0},
            {"componente": "MP-301", "quantidade": 1.0},
        ],
        "PA-002": [
            {"componente": "SA-010", "quantidade": 1.0},
            {"componente": "MP-300", "quantidade": 1.0},
            {"componente": "MP-302", "quantidade": 1.0},
        ],
        "SA-010": [
            {"componente": "MP-100", "quantidade": 3.0},
            {"componente": "MP-101", "quantidade": 0.5},
        ],
        "SA-020": [
            {"componente": "MP-200", "quantidade": 1.0},
            {"componente": "MP-201", "quantidade": 36.0},
            {"componente": "MP-202", "quantidade": 1.0},
        ],
    }

    estoque_demo = {
        "PA-001": 5.0,
        "PA-002": 4.0,
        "SA-010": 12.0,
        "SA-020": 40.0,
        "MP-100": 90.0,
        "MP-101": 25.0,
        "MP-200": 60.0,
        "MP-201": 1500.0,
        "MP-202": 18.0,
        "MP-300": 30.0,
        "MP-301": 15.0,
        "MP-302": 20.0,
    }

    centros_demo = {
        "CT-01": {
            "descricao": "Solda e Pintura de Quadros",
            "capacidade_semanal": 24.0,
            "custo_hora": 30.00,
        },
        "CT-02": {
            "descricao": "Montagem de Rodas",
            "capacidade_semanal": 30.0,
            "custo_hora": 32.00,
        },
        "CT-03": {
            "descricao": "Montagem Final",
            "capacidade_semanal": 16.0,
            "custo_hora": 40.00,
        },
    }

    roteiros_demo = {
        "PA-001": {"centro": "CT-03", "tempo_unitario": 0.5},
        "PA-002": {"centro": "CT-03", "tempo_unitario": 0.4},
        "SA-010": {"centro": "CT-01", "tempo_unitario": 0.5},
        "SA-020": {"centro": "CT-02", "tempo_unitario": 0.25},
    }

    mps_demo = {
        "PA-001": [10, 30, 0, 40, 25, 0, 35, 30],
        "PA-002": [5, 10, 15, 10, 10, 15, 10, 5],
    }

    ordens_demo = [
        {
            "numero": "OP-0001",
            "tipo": "OP",
            "item": "SA-020",
            "quantidade": 50.0,
            "semana_liberacao": 0,
            "semana_entrega": 1,
            "status": "FIRME",
        }
    ]

    salvar_json("itens", itens_demo)
    salvar_json("estrutura", estrutura_demo)
    salvar_json("estoque", estoque_demo)
    salvar_json("centros", centros_demo)
    salvar_json("roteiros", roteiros_demo)
    salvar_json("mps", mps_demo)
    salvar_json("ordens", ordens_demo)

    for codigo, saldo in estoque_demo.items():
        registrar_movimento_csv(
            "01/10/2026", codigo, "ENTRADA", saldo, saldo, "Saldo Inicial Demo"
        )