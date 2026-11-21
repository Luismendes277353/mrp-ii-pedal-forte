import json
import os
from persistencia import PASTA_DATA, carregar_json, salvar_json

ARQUIVO_HISTORICO = os.path.join(PASTA_DATA, "historico_vendas.json")


def carregar_ou_criar_historico_vendas() -> dict[str, list[float]]:
    os.makedirs(PASTA_DATA, exist_ok=True)
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)

    historico_padrao = {
        "PA-001": [8, 12, 10, 15, 11, 16, 14, 20, 15, 22, 19, 26],
        "PA-002": [6, 8, 9, 7, 7, 10, 11, 8, 8, 11, 12, 10],
    }
    with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as arquivo:
        json.dump(historico_padrao, arquivo, indent=4, ensure_ascii=False)
    return historico_padrao


def prever_demanda_ia(codigo_pa: str, horizonte: int = 8) -> dict:
    historico_total = carregar_ou_criar_historico_vendas()
    serie = [float(v) for v in historico_total.get(codigo_pa, [])]

    if len(serie) < 4:
        serie = [10.0, 12.0, 11.0, 14.0]

    n = len(serie)
    tempos = list(range(1, n + 1))

    media_t = sum(tempos) / n
    media_y = sum(serie) / n

    numerador = sum((t - media_t) * (y - media_y) for t, y in zip(tempos, serie))
    denominador = sum((t - media_t) ** 2 for t in tempos)
    b = numerador / denominador if denominador != 0 else 0.0
    a = media_y - b * media_t

    fatores_brutos: dict[int, list[float]] = {0: [], 1: [], 2: [], 3: []}
    for idx, (t, y_real) in enumerate(zip(tempos, serie)):
        tendencia = max(1.0, a + b * t)
        fatores_brutos[idx % 4].append(y_real / tendencia)

    indices_sazonais = []
    for k in range(4):
        lista_k = fatores_brutos[k]
        indices_sazonais.append(sum(lista_k) / len(lista_k) if lista_k else 1.0)

    fator_norm = 4.0 / sum(indices_sazonais)
    indices_sazonais = [round(idx_s * fator_norm, 4) for idx_s in indices_sazonais]

    erros_pct = []
    for idx, (t, y_real) in enumerate(zip(tempos, serie)):
        if y_real > 0:
            y_est = max(0.0, (a + b * t) * indices_sazonais[idx % 4])
            erros_pct.append(abs(y_real - y_est) / y_real)
    mape = round((sum(erros_pct) / len(erros_pct) * 100.0) if erros_pct else 0.0, 2)

    previsao: list[float] = []
    for passo in range(1, horizonte + 1):
        t_futuro = n + passo
        idx_ciclo = (t_futuro - 1) % 4
        valor_previsto = (a + b * t_futuro) * indices_sazonais[idx_ciclo]
        previsao.append(float(max(0, round(valor_previsto))))

    return {
        "codigo": codigo_pa,
        "historico": serie,
        "previsao": previsao,
        "intercepto": round(a, 3),
        "inclinacao": round(b, 3),
        "indices_sazonais": indices_sazonais,
        "mape": mape,
    }


def executar_previsao_ia_cli() -> None:
    itens = carregar_json("itens")
    mps = carregar_json("mps")

    produtos_pa = sorted([cod for cod, d in itens.items() if d["tipo"] == "PA"])
    if not produtos_pa:
        print("Nenhum Produto Acabado (PA) cadastrado.")
        return

    print("\n--- IA: PREVISÃO DE DEMANDA (TENDÊNCIA + SAZONALIDADE) ---")
    for idx, cod in enumerate(produtos_pa, start=1):
        print(f"{idx}. {cod} - {itens[cod]['descricao']}")

    codigo = input("Informe o código do PA (ex.: PA-001): ").strip().upper()
    if codigo not in itens or itens[codigo]["tipo"] != "PA":
        print("ERRO: Informe um código de Produto Acabado (PA) válido.")
        return

    resultado = prever_demanda_ia(codigo, horizonte=8)
    sinal = "+" if resultado["inclinacao"] >= 0 else ""

    print(f"\nModelo treinado para {codigo} - {itens[codigo]['descricao']}:")
    print(f"  - Equação de tendência: Y(t) = {resultado['intercepto']} {sinal}{resultado['inclinacao']}*t")
    print(f"  - Índices sazonais (ciclo 4 sem): {resultado['indices_sazonais']}")
    print(f"  - Erro médio percentual (MAPE): {resultado['mape']}%")
    print(f"  - Histórico (12 sem): {[int(x) for x in resultado['historico']]}")
    print(f"  - Previsão IA (S1..S8): {[int(x) for x in resultado['previsao']]}")

    confirmar = input("\nDeseja aplicar esta previsão diretamente no MPS? [S/N]: ").strip().upper()
    if confirmar == "S":
        mps[codigo] = resultado["previsao"]
        salvar_json("mps", mps)
        print(f"MPS de {codigo} atualizado com sucesso pela IA!")