"""Previsao de demanda para o MPS (bonus - IA / aprendizado de maquina leve).

A partir do historico semanal de demanda real de um produto acabado, o
sistema **aprende** o melhor modelo e seus parametros e preve as proximas
8 semanas, sugerindo o preenchimento do MPS.

Tudo e implementado do zero, apenas com a biblioteca padrao (RNF08):

* cinco modelos classicos de series temporais (ingenuo, media movel,
  suavizacao exponencial simples, Holt com tendencia e regressao linear);
* ajuste de parametros por busca em grade, minimizando o erro de previsao
  um passo a frente (validacao "rolling origin");
* selecao automatica do modelo pelo menor erro medio absoluto (MAE) nas
  ultimas semanas do historico, que ficam reservadas para teste
  (hold-out), isto e, o modelo e avaliado em dados que nao viu no ajuste.

Historico em ``dados["historico"]``::

    {"PA-001": [12, 15, 14, ...]}   # mais antigo primeiro, 1 valor/semana
"""

import math
from itertools import product

import mps
from itens import obter_item
from utils import (
    HORIZONTE,
    ErroNegocio,
    arredondar,
    formatar_numero,
    montar_tabela,
    validar_numero,
)

MINIMO_HISTORICO = 8
SEMANAS_VALIDACAO = 6
Z_FAIXA_80 = 1.28  # faixa de ~80% sob erros aproximadamente normais


def ingenuo(serie, horizonte):
    """Repete o ultimo valor observado (referencia para comparacao)."""
    return [float(serie[-1])] * horizonte


def media_movel(serie, horizonte, janela=4):
    """Media das ultimas `janela` semanas."""
    janela = max(1, min(janela, len(serie)))
    return [sum(serie[-janela:]) / janela] * horizonte


def suavizacao_exponencial(serie, horizonte, alpha=0.3):
    """Suavizacao exponencial simples: nivel ponderado pelo passado."""
    nivel = float(serie[0])
    for valor in serie[1:]:
        nivel = alpha * valor + (1 - alpha) * nivel
    return [nivel] * horizonte


def holt(serie, horizonte, alpha=0.3, beta=0.1):
    """Suavizacao exponencial de Holt: nivel + tendencia linear."""
    nivel = float(serie[0])
    tendencia = float(serie[1] - serie[0])
    for valor in serie[1:]:
        anterior = nivel
        nivel = alpha * valor + (1 - alpha) * (nivel + tendencia)
        tendencia = beta * (nivel - anterior) + (1 - beta) * tendencia
    return [nivel + passo * tendencia for passo in range(1, horizonte + 1)]


def regressao_linear(serie, horizonte):
    """Reta de minimos quadrados ordinarios y = a + b*t, extrapolada."""
    n = len(serie)
    media_x = (n - 1) / 2
    media_y = sum(serie) / n
    sxx = sum((x - media_x) ** 2 for x in range(n))
    sxy = sum((x - media_x) * (y - media_y) for x, y in enumerate(serie))
    inclinacao = sxy / sxx if sxx else 0.0
    intercepto = media_y - inclinacao * media_x
    return [intercepto + inclinacao * (n - 1 + passo)
            for passo in range(1, horizonte + 1)]


# nome -> (rotulo, funcao, grade de parametros)
MODELOS = {
    "ingenuo": ("Ingenuo (ultimo valor)", ingenuo, {}),
    "media_movel": ("Media movel", media_movel,
                    {"janela": (3, 4, 6, 8)}),
    "suavizacao_exponencial": (
        "Suavizacao exponencial", suavizacao_exponencial,
        {"alpha": (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)}),
    "holt": ("Holt (tendencia)", holt,
             {"alpha": (0.1, 0.3, 0.5, 0.7, 0.9),
              "beta": (0.05, 0.1, 0.2, 0.3, 0.5)}),
    "regressao_linear": ("Regressao linear", regressao_linear, {}),
}


def _combinacoes(grade):
    """Todas as combinacoes de parametros de uma grade (lista de dicts)."""
    if not grade:
        return [{}]
    nomes = list(grade)
    return [dict(zip(nomes, valores))
            for valores in product(*(grade[nome] for nome in nomes))]


def _erro_um_passo(funcao, serie, parametros):
    """Erro absoluto medio prevendo 1 semana a frente ao longo da serie."""
    inicio = max(4, len(serie) // 3)
    erros = [abs(funcao(serie[:t], 1, **parametros)[0] - serie[t])
             for t in range(inicio, len(serie))]
    return sum(erros) / len(erros)


def ajustar_parametros(chave, serie):
    """Busca em grade os parametros de menor erro um passo a frente."""
    _, funcao, grade = MODELOS[chave]
    candidatos = _combinacoes(grade)
    if len(candidatos) == 1:
        return candidatos[0]
    return min(candidatos,
               key=lambda p: _erro_um_passo(funcao, serie, p))


def _metricas(reais, previstos):
    """MAE e RMSE entre valores reais e previstos."""
    diferencas = [r - p for r, p in zip(reais, previstos)]
    mae = sum(abs(d) for d in diferencas) / len(diferencas)
    rmse = math.sqrt(sum(d * d for d in diferencas) / len(diferencas))
    return mae, rmse


def _inteiro_nao_negativo(valor):
    """Arredonda para a unidade mais proxima (meio sobe), minimo zero."""
    return max(0, int(math.floor(valor + 0.5)))


def prever_demanda(historico, horizonte=HORIZONTE):
    """Treina, avalia e escolhe o melhor modelo; preve o proximo periodo.

    Retorna um dicionario com o modelo escolhido, seus parametros, a
    previsao (inteiros >= 0), a faixa de ~80% e a avaliacao de todos os
    modelos no conjunto de teste.
    """
    serie = [float(valor) for valor in historico]
    if len(serie) < MINIMO_HISTORICO:
        raise ErroNegocio(
            f"historico insuficiente: sao necessarias pelo menos "
            f"{MINIMO_HISTORICO} semanas (ha {len(serie)}).")
    teste = min(SEMANAS_VALIDACAO, len(serie) // 3)
    treino, reais = serie[:-teste], serie[-teste:]

    avaliacao = []
    for ordem, (chave, (rotulo, funcao, _)) in enumerate(MODELOS.items()):
        parametros = ajustar_parametros(chave, treino)
        previstos = funcao(treino, teste, **parametros)
        mae, rmse = _metricas(reais, previstos)
        avaliacao.append({"modelo": chave, "rotulo": rotulo,
                          "parametros": parametros, "mae": mae,
                          "rmse": rmse, "ordem": ordem})
    avaliacao.sort(key=lambda a: (round(a["mae"], 9), a["ordem"]))
    melhor = avaliacao[0]

    # Reajusta o modelo vencedor com todo o historico e preve o futuro.
    _, funcao, _ = MODELOS[melhor["modelo"]]
    parametros = ajustar_parametros(melhor["modelo"], serie)
    bruta = funcao(serie, horizonte, **parametros)
    margem = Z_FAIXA_80 * melhor["rmse"]
    return {
        "modelo": melhor["modelo"],
        "rotulo": melhor["rotulo"],
        "parametros": parametros,
        "previsao": [_inteiro_nao_negativo(v) for v in bruta],
        "previsao_bruta": [arredondar(v) for v in bruta],
        "faixa_inferior": [_inteiro_nao_negativo(v - margem) for v in bruta],
        "faixa_superior": [_inteiro_nao_negativo(v + margem)
                           for v in bruta],
        "erro_mae": melhor["mae"],
        "erro_rmse": melhor["rmse"],
        "semanas_teste": teste,
        "avaliacao": avaliacao,
        "historico": [int(v) if v == int(v) else v for v in serie],
    }


def _obter_pa(dados, codigo):
    item = obter_item(dados, codigo)
    if item["tipo"] != "PA":
        raise ErroNegocio(
            f"{item['codigo']} nao e produto acabado: a previsao de demanda "
            "vale apenas para itens PA.")
    return item


def obter_historico(dados, codigo):
    """Historico semanal de demanda real de um PA (lista, pode ser vazia)."""
    item = _obter_pa(dados, codigo)
    return list(dados.get("historico", {}).get(item["codigo"], []))


def registrar_historico(dados, codigo, quantidades):
    """Substitui o historico de demanda real de um PA."""
    item = _obter_pa(dados, codigo)
    for quantidade in quantidades:
        validar_numero(quantidade, "A demanda", minimo=0)
    dados.setdefault("historico", {})[item["codigo"]] = [
        arredondar(q) for q in quantidades]


def adicionar_demanda_real(dados, codigo, quantidade):
    """Acrescenta a demanda real de mais uma semana ao historico."""
    item = _obter_pa(dados, codigo)
    validar_numero(quantidade, "A demanda", minimo=0)
    dados.setdefault("historico", {}).setdefault(
        item["codigo"], []).append(arredondar(quantidade))


def prever_demanda_pa(dados, codigo):
    """Previsao das proximas 8 semanas de um PA a partir do historico."""
    item = _obter_pa(dados, codigo)
    resultado = prever_demanda(obter_historico(dados, item["codigo"]))
    resultado["codigo"] = item["codigo"]
    return resultado


def aplicar_previsao_ao_mps(dados, codigo, resultado):
    """Grava a previsao como demanda das 8 semanas do MPS do PA."""
    mps.definir_plano(dados, codigo, resultado["previsao"])


def formatar_previsao(resultado):
    """Texto com o desempenho dos modelos e a previsao das 8 semanas."""
    parametros = ", ".join(f"{k}={formatar_numero(v)}"
                           for k, v in resultado["parametros"].items())
    saida = [
        f"PREVISAO DE DEMANDA - {resultado.get('codigo', '')}".rstrip(" -"),
        f"Historico: {len(resultado['historico'])} semanas | teste "
        f"(hold-out): ultimas {resultado['semanas_teste']} semanas",
        "",
    ]
    linhas = []
    for aval in resultado["avaliacao"]:
        marca = "<== escolhido" if aval["modelo"] == resultado["modelo"] \
            else ""
        linhas.append((aval["rotulo"], formatar_numero(aval["mae"], 2),
                       formatar_numero(aval["rmse"], 2), marca))
    saida.extend(montar_tabela(("Modelo", "MAE", "RMSE", ""), linhas,
                               "<>><"))
    saida.append("")
    saida.append(f"Modelo escolhido: {resultado['rotulo']}"
                 + (f" ({parametros})" if parametros else ""))
    cabecalho = ["Semana"] + [str(s) for s in range(1, HORIZONTE + 1)]
    linhas = [
        ["Previsao"] + [str(v) for v in resultado["previsao"]],
        ["Faixa min."] + [str(v) for v in resultado["faixa_inferior"]],
        ["Faixa max."] + [str(v) for v in resultado["faixa_superior"]],
    ]
    saida.extend(montar_tabela(cabecalho, linhas, "<" + ">" * HORIZONTE))
    return saida
