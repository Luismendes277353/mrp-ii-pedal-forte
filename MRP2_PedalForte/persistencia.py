"""Leitura e gravacao de arquivos na pasta data/ (RF15, RNF07).

Arquivos:
    itens.json, estrutura.json, estoque.json, centros.json, roteiros.json,
    mps.json, ordens.json, mrp.json (resultado do ultimo MRP),
    historico.json (demanda real semanal, usada na previsao) e
    movimentos.csv (kardex).

Este modulo tambem monta a base de demonstracao da fabrica fictícia
(RNF09), usando as mesmas funcoes de negocio do sistema para que os dados
gerados sejam sempre consistentes (saldos = soma dos movimentos).
"""

import csv
import io
import json
import os
from pathlib import Path

import capacidade
import custos
import estrutura
import estoque
import itens
import mps
import ordens
import previsao

RAIZ = Path(__file__).resolve().parent
PASTA_DATA = RAIZ / "data"
PASTA_SAIDA = RAIZ / "saida"

ARQUIVOS_JSON = {
    "itens": "itens.json",
    "estrutura": "estrutura.json",
    "estoque": "estoque.json",
    "centros": "centros.json",
    "roteiros": "roteiros.json",
    "mps": "mps.json",
    "ordens": "ordens.json",
    "mrp": "mrp.json",
    "historico": "historico.json",
}
ARQUIVO_MOVIMENTOS = "movimentos.csv"
CAMPOS_MOVIMENTOS = ("id", "data", "codigo", "tipo", "quantidade", "saldo",
                     "documento")
TIPOS_ESPERADOS = {
    "itens": dict, "estrutura": dict, "estoque": dict, "centros": dict,
    "roteiros": dict, "mps": dict, "ordens": list, "mrp": dict,
    "historico": dict,
}


class ErroPersistencia(Exception):
    """Falha ao ler ou gravar os arquivos de dados."""


def criar_dados_vazios():
    """Estrutura de dados vazia usada pelo sistema."""
    return {
        "itens": {},
        "estrutura": {},
        "estoque": {},
        "movimentos": [],
        "centros": {},
        "roteiros": {},
        "mps": {},
        "ordens": [],
        "mrp": {"executado_em": None, "registros": {}, "mensagens": []},
        "historico": {},
    }


def base_existe(pasta=PASTA_DATA):
    """Indica se ja existe uma base de dados gravada."""
    return (Path(pasta) / ARQUIVOS_JSON["itens"]).is_file()


def _ler_json(caminho, padrao):
    if not caminho.is_file():
        return padrao
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except (json.JSONDecodeError, OSError) as erro:
        raise ErroPersistencia(
            f"nao foi possivel ler {caminho.name}: {erro}") from erro


def _ler_movimentos(caminho):
    if not caminho.is_file():
        return []
    movimentos = []
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            for linha in csv.DictReader(arquivo, delimiter=";"):
                movimentos.append({
                    "id": int(linha["id"]),
                    "data": linha["data"],
                    "codigo": linha["codigo"],
                    "tipo": linha["tipo"],
                    "quantidade": float(linha["quantidade"]),
                    "saldo": float(linha["saldo"]),
                    "documento": linha["documento"],
                })
    except (KeyError, ValueError, OSError) as erro:
        raise ErroPersistencia(
            f"nao foi possivel ler {caminho.name}: {erro}") from erro
    return movimentos


def carregar_tudo(pasta=PASTA_DATA):
    """Carrega todos os arquivos da pasta data/ (RF15)."""
    pasta = Path(pasta)
    dados = criar_dados_vazios()
    for chave, nome in ARQUIVOS_JSON.items():
        conteudo = _ler_json(pasta / nome, dados[chave])
        if not isinstance(conteudo, TIPOS_ESPERADOS[chave]):
            raise ErroPersistencia(
                f"formato inesperado em {nome}: esperado "
                f"{TIPOS_ESPERADOS[chave].__name__}.")
        dados[chave] = conteudo
    dados["movimentos"] = _ler_movimentos(pasta / ARQUIVO_MOVIMENTOS)
    return dados


def _gravar_texto(caminho, conteudo):
    temporario = caminho.with_name(caminho.name + ".tmp")
    try:
        with open(temporario, "w", encoding="utf-8", newline="") as arquivo:
            arquivo.write(conteudo)
        os.replace(temporario, caminho)
    except OSError as erro:
        raise ErroPersistencia(
            f"nao foi possivel gravar {caminho.name}: {erro}") from erro


def salvar_tudo(dados, pasta=PASTA_DATA):
    """Grava todos os dados na pasta data/."""
    pasta = Path(pasta)
    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        raise ErroPersistencia(
            f"nao foi possivel criar a pasta {pasta}: {erro}") from erro
    for chave, nome in ARQUIVOS_JSON.items():
        texto = json.dumps(dados[chave], ensure_ascii=False, indent=2)
        _gravar_texto(pasta / nome, texto + "\n")

    saida = io.StringIO()
    escritor = csv.DictWriter(saida, fieldnames=CAMPOS_MOVIMENTOS,
                              delimiter=";", lineterminator="\n")
    escritor.writeheader()
    for movimento in dados["movimentos"]:
        escritor.writerow({campo: movimento[campo]
                           for campo in CAMPOS_MOVIMENTOS})
    _gravar_texto(pasta / ARQUIVO_MOVIMENTOS, saida.getvalue())


def inicializar(pasta=PASTA_DATA):
    """Carrega a base existente ou cria a base de demonstracao.

    Retorna ``(dados, base_criada)``.
    """
    if base_existe(pasta):
        return carregar_tudo(pasta), False
    dados = gerar_base_demo()
    salvar_tudo(dados, pasta)
    return dados, True


# codigo, descricao, unidade, custo, lead time, est. seguranca, lote minimo
_ITENS_DEMO = (
    ("PA-001", "Bicicleta Aro 29 MTB", "un", 0, 1, 0, 5),
    ("PA-002", "Bicicleta Aro 26 Urbana", "un", 0, 1, 0, 5),
    ("SA-010", "Quadro aro 29 soldado", "un", 0, 1, 10, 40),
    ("SA-020", "Roda aro 29 montada", "un", 0, 1, 10, 80),
    ("SA-030", "Quadro aro 26 soldado", "un", 0, 1, 5, 20),
    ("SA-040", "Roda aro 26 montada", "un", 0, 1, 5, 40),
    ("MP-100", "Tubo de aco carbono", "m", 18.00, 2, 60, 200),
    ("MP-101", "Tinta epoxi", "L", 40.00, 2, 5, 20),
    ("MP-200", "Aro 29 aluminio", "un", 35.00, 2, 20, 100),
    ("MP-201", "Raio inox", "un", 0.60, 2, 360, 2000),
    ("MP-202", "Pneu 29 x 2.20", "un", 52.00, 2, 20, 60),
    ("MP-210", "Aro 26 aluminio", "un", 30.00, 2, 10, 50),
    ("MP-211", "Pneu 26 x 1.95", "un", 42.00, 2, 10, 50),
    ("MP-300", "Guidao", "un", 45.00, 1, 10, 50),
    ("MP-301", "Kit transmissao 12v", "un", 320.00, 3, 10, 30),
    ("MP-302", "Kit transmissao 21v", "un", 210.00, 2, 10, 30),
)

# pai, componente, quantidade por unidade
_BOM_DEMO = (
    ("PA-001", "SA-010", 1), ("PA-001", "SA-020", 2),
    ("PA-001", "MP-300", 1), ("PA-001", "MP-301", 1),
    ("SA-010", "MP-100", 3), ("SA-010", "MP-101", 0.5),
    ("SA-020", "MP-200", 1), ("SA-020", "MP-201", 36),
    ("SA-020", "MP-202", 1),
    ("PA-002", "SA-030", 1), ("PA-002", "SA-040", 2),
    ("PA-002", "MP-300", 1), ("PA-002", "MP-302", 1),
    ("SA-030", "MP-100", 2.5), ("SA-030", "MP-101", 0.4),
    ("SA-040", "MP-210", 1), ("SA-040", "MP-201", 32),
    ("SA-040", "MP-211", 1),
)

# codigo, descricao, capacidade (h/semana), custo-hora
_CENTROS_DEMO = (
    ("CT-01", "Soldagem e pintura de quadros", 50, 45.00),
    ("CT-02", "Montagem de rodas", 70, 39.00),
    ("CT-03", "Montagem final", 16, 40.00),
)

# item, centro, horas por unidade
_ROTEIROS_DEMO = (
    ("SA-010", "CT-01", 1.2), ("SA-030", "CT-01", 1.0),
    ("SA-020", "CT-02", 0.8), ("SA-040", "CT-02", 0.7),
    ("PA-001", "CT-03", 0.5), ("PA-002", "CT-03", 0.4),
)

_MPS_DEMO = {
    "PA-001": [10, 30, 0, 40, 25, 0, 35, 30],
    "PA-002": [0, 0, 20, 0, 0, 15, 0, 0],
}

# Demanda real semanal (26 semanas, mais antiga primeiro) para a previsao
_HISTORICO_DEMO = {
    "PA-001": [16, 18, 13, 18, 20, 20, 16, 15, 17, 13, 16, 14, 19, 18, 23,
               28, 29, 29, 22, 26, 23, 21, 24, 25, 30, 26],
    "PA-002": [9, 3, 8, 9, 8, 10, 8, 9, 9, 6, 7, 8, 8, 8, 9, 12, 10, 11,
               12, 12, 10, 8, 7, 10, 10, 12],
}

# item, quantidade, documento (todas em 01/10/2026)
_COMPRAS_INICIAIS_DEMO = (
    ("MP-100", 500, "NF 4510 - Aco Centro-Oeste"),
    ("MP-101", 100, "NF 4511 - Tintas Divinopolis"),
    ("MP-200", 300, "NF 4512 - Aros Minas"),
    ("MP-201", 8000, "NF 4513 - Raios do Sul"),
    ("MP-202", 60, "NF 4521 - Pneus Minas"),
    ("MP-210", 100, "NF 4514 - Aros Minas"),
    ("MP-211", 100, "NF 4515 - Pneus Minas"),
    ("MP-300", 50, "NF 4516 - Cicle Pecas"),
    ("MP-301", 40, "NF 4517 - Cicle Pecas"),
    ("MP-302", 30, "NF 4518 - Cicle Pecas"),
)


def _produzir_historico(dados, item, quantidade, data):
    """Cria uma OP liberada e a aponta na data informada (historico)."""
    ordem = ordens.criar_ordem(dados, "OP", item, quantidade, 0, 1,
                               status=ordens.LIBERADA, data=data)
    ordem["atrasada"] = False
    ordens.apontar_producao(dados, ordem["numero"], data)


def _gerar_ordens_demo(dados):
    """Ordens ja existentes na base: encerradas e programadas."""
    for item, quantidade, documento in _COMPRAS_INICIAIS_DEMO:
        estoque.registrar_movimento(dados, item, "ENTRADA", quantidade,
                                    documento, "2026-10-01")
    # OCs que originaram as compras de pneus e raios (ja recebidas)
    for item, quantidade in (("MP-202", 60), ("MP-201", 8000)):
        compra = ordens.criar_ordem(
            dados, "OC", item, quantidade, -1, 1, status=ordens.ENCERRADA,
            data="2026-09-24")
        compra["atrasada"] = False
        compra["data_encerramento"] = "2026-10-01"

    _produzir_historico(dados, "SA-010", 40, "2026-10-02")
    _produzir_historico(dados, "SA-030", 20, "2026-10-03")
    _produzir_historico(dados, "SA-020", 40, "2026-10-05")
    _produzir_historico(dados, "SA-040", 20, "2026-10-06")
    estoque.registrar_movimento(dados, "MP-202", "AJUSTE", -2,
                                "Inventario mensal", "2026-10-07")

    # Ordens programadas (recebimentos programados do MRP)
    producao = ordens.criar_ordem(dados, "OP", "SA-020", 50, 0, 1,
                                  status=ordens.LIBERADA, data="2026-10-08")
    producao["atrasada"] = False
    compra = ordens.criar_ordem(dados, "OC", "MP-202", 60, -1, 1,
                                status=ordens.LIBERADA, data="2026-10-08")
    compra["atrasada"] = False


def gerar_base_demo():
    """Monta a base de demonstracao completa e consistente (RNF09)."""
    dados = criar_dados_vazios()
    for dados_item in _ITENS_DEMO:
        itens.cadastrar_item(dados, *dados_item)
    for pai, componente, quantidade in _BOM_DEMO:
        estrutura.adicionar_componente(dados, pai, componente, quantidade)
    for codigo, descricao, horas, custo_hora in _CENTROS_DEMO:
        capacidade.cadastrar_centro(dados, codigo, descricao, horas,
                                    custo_hora)
    for item, centro, tempo in _ROTEIROS_DEMO:
        capacidade.definir_roteiro(dados, item, centro, tempo)
    for codigo, plano in _MPS_DEMO.items():
        mps.definir_plano(dados, codigo, plano)
    for codigo, serie in _HISTORICO_DEMO.items():
        previsao.registrar_historico(dados, codigo, serie)
    custos.atualizar_custos_unitarios(dados)
    _gerar_ordens_demo(dados)
    return dados
