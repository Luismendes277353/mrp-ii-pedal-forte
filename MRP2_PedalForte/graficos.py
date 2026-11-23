"""Graficos de gestao e acompanhamento com matplotlib (RF16).

Duas camadas:

* ``figura_*``: desenham o grafico em uma ``Figure`` recebida (usadas pela
  interface grafica, que embute a figura em uma janela Tkinter);
* ``grafico_*``: criam a figura, salvam um PNG na pasta saida/ e, quando ha
  ambiente grafico, tambem a exibem na tela. Retornam ``(caminho, exibido)``.

A preparacao dos dados (funcoes ``dados_*``) e separada do desenho, o que
permite testar a logica sem depender do matplotlib.
"""

import capacidade
import estoque
import mrp
import ordens
from itens import obter_item
from persistencia import PASTA_SAIDA
from utils import HORIZONTE, ErroNegocio

COR_NORMAL = "#2e86c1"
COR_ALERTA = "#c0392b"
COR_REFERENCIA = "#f5b041"
COR_OP = "#2e86c1"
COR_OC = "#e67e22"
SEMANAS = list(range(1, HORIZONTE + 1))


def dados_posicao_estoque(dados):
    """Codigos, saldos e estoques de seguranca de todos os itens."""
    posicoes = estoque.posicao_estoque(dados)
    return {
        "codigos": [p["codigo"] for p in posicoes],
        "saldos": [p["saldo"] for p in posicoes],
        "seguranca": [p["estoque_seguranca"] for p in posicoes],
    }


def dados_estoque_projetado(dados, codigo):
    """Estoque projetado de um item nas 8 semanas do MRP."""
    item = obter_item(dados, codigo)
    registro = mrp.obter_registro(dados, codigo)
    return {"item": item, "ep": registro["ep"],
            "seguranca": item["estoque_seguranca"]}


def dados_ordens_por_semana(dados):
    """Quantidade de OPs e OCs abertas por semana de entrega (chegada)."""
    contagem = {"OP": [0] * HORIZONTE, "OC": [0] * HORIZONTE}
    for ordem in ordens.listar_ordens(dados, abertas=True):
        semana = ordem["semana_entrega"]
        if 1 <= semana <= HORIZONTE:
            contagem[ordem["tipo"]][semana - 1] += 1
    return contagem


def dados_carga_capacidade(dados, codigo_centro):
    """Carga semanal, capacidade e semanas de sobrecarga de um centro."""
    centro = capacidade.obter_centro(dados, codigo_centro)
    linhas = capacidade.analisar_centro(dados, centro["codigo"])
    return {"centro": centro,
            "cargas": [linha["carga"] for linha in linhas],
            "sobrecarga": [linha["sobrecarga"] for linha in linhas]}


def exigir_matplotlib():
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        raise ErroNegocio(
            "a biblioteca matplotlib nao esta instalada. "
            "Execute: pip install matplotlib") from None


def _preparar_pyplot():
    exigir_matplotlib()
    import matplotlib.pyplot as plt
    return plt


def _finalizar(plt, figura, nome_arquivo, mostrar):
    """Salva o PNG e, se possivel, exibe o grafico na tela."""
    try:
        PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
        caminho = PASTA_SAIDA / nome_arquivo
        figura.tight_layout()
        figura.savefig(caminho, dpi=120)
    except OSError as erro:
        plt.close(figura)
        raise ErroNegocio(
            f"nao foi possivel salvar {nome_arquivo}: {erro}") from erro
    exibido = False
    if mostrar and plt.get_backend().lower() != "agg":
        plt.show()
        exibido = True
    plt.close(figura)
    return caminho, exibido


def _gerar_arquivo(desenhar, tamanho, nome_arquivo, mostrar):
    """Cria a figura, desenha, salva em PNG e exibe (se houver tela)."""
    plt = _preparar_pyplot()
    figura = plt.figure(figsize=tamanho)
    try:
        desenhar(figura)
    except Exception:
        plt.close(figura)
        raise
    return _finalizar(plt, figura, nome_arquivo, mostrar)


def figura_posicao_estoque(dados, figura):
    """Saldo atual x estoque de seguranca de cada item (barras)."""
    exigir_matplotlib()
    from matplotlib.patches import Patch

    serie = dados_posicao_estoque(dados)
    posicoes = list(range(len(serie["codigos"])))
    largura = 0.4
    cores = [COR_ALERTA if saldo < minimo else COR_NORMAL
             for saldo, minimo in zip(serie["saldos"], serie["seguranca"])]

    eixo = figura.subplots()
    eixo.bar([p - largura / 2 for p in posicoes], serie["saldos"], largura,
             color=cores)
    eixo.bar([p + largura / 2 for p in posicoes], serie["seguranca"],
             largura, color=COR_REFERENCIA)
    eixo.set_yscale("symlog", linthresh=1)
    eixo.set_xticks(posicoes)
    eixo.set_xticklabels(serie["codigos"], rotation=45, ha="right")
    eixo.set_ylabel("Quantidade (escala symlog)")
    eixo.set_title("Posicao de estoque: saldo atual x estoque de seguranca")
    eixo.grid(axis="y", alpha=0.3)
    eixo.legend(handles=[
        Patch(color=COR_NORMAL, label="Saldo acima do estoque de seguranca"),
        Patch(color=COR_ALERTA, label="Saldo abaixo do estoque de seguranca"),
        Patch(color=COR_REFERENCIA, label="Estoque de seguranca"),
    ])
    return figura


def figura_estoque_projetado(dados, codigo, figura):
    """Estoque projetado de um item nas 8 semanas, com a linha do ES."""
    serie = dados_estoque_projetado(dados, codigo)
    exigir_matplotlib()
    item = serie["item"]

    eixo = figura.subplots()
    eixo.plot(SEMANAS, serie["ep"], marker="o", color=COR_NORMAL,
              label="Estoque projetado")
    eixo.axhline(serie["seguranca"], color=COR_ALERTA, linestyle="--",
                 label=f"Estoque de seguranca ({serie['seguranca']:g})")
    for semana, valor in zip(SEMANAS, serie["ep"]):
        eixo.annotate(f"{valor:g}", (semana, valor),
                      textcoords="offset points", xytext=(0, 8),
                      ha="center", fontsize=8)
    eixo.set_xticks(SEMANAS)
    eixo.set_xlabel("Semana")
    eixo.set_ylabel(f"Quantidade ({item['unidade']})")
    eixo.set_title(f"Estoque projetado - {item['codigo']} "
                   f"{item['descricao']}")
    topo = max(max(serie["ep"]), serie["seguranca"], 1)
    eixo.set_ylim(0, topo * 1.2)
    eixo.grid(alpha=0.3)
    eixo.legend()
    return figura


def figura_ordens_por_semana(dados, figura):
    """OPs e OCs por semana de entrega (barras empilhadas)."""
    exigir_matplotlib()
    from matplotlib.ticker import MaxNLocator

    contagem = dados_ordens_por_semana(dados)
    eixo = figura.subplots()
    eixo.bar(SEMANAS, contagem["OP"], color=COR_OP,
             label="Ordens de producao (OP)")
    eixo.bar(SEMANAS, contagem["OC"], bottom=contagem["OP"], color=COR_OC,
             label="Ordens de compra (OC)")
    eixo.set_xticks(SEMANAS)
    eixo.yaxis.set_major_locator(MaxNLocator(integer=True))
    eixo.set_xlabel("Semana de entrega (chegada)")
    eixo.set_ylabel("Numero de ordens abertas")
    eixo.set_title("Ordens de producao e de compra por semana de entrega")
    eixo.grid(axis="y", alpha=0.3)
    eixo.legend()
    return figura


def figura_carga_capacidade(dados, codigo_centro, figura):
    """Carga x capacidade de um centro por semana, destacando sobrecargas."""
    serie = dados_carga_capacidade(dados, codigo_centro)
    exigir_matplotlib()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch

    centro = serie["centro"]
    cores = [COR_ALERTA if sobre else COR_NORMAL
             for sobre in serie["sobrecarga"]]
    eixo = figura.subplots()
    eixo.bar(SEMANAS, serie["cargas"], color=cores)
    eixo.axhline(centro["capacidade"], color="black", linestyle="--")
    for semana, carga, sobre in zip(SEMANAS, serie["cargas"],
                                    serie["sobrecarga"]):
        if sobre:
            eixo.annotate("SOBRECARGA", (semana, carga),
                          textcoords="offset points", xytext=(0, 4),
                          ha="center", fontsize=8, color=COR_ALERTA)
    topo = max(max(serie["cargas"]), centro["capacidade"])
    eixo.set_ylim(0, topo * 1.3)
    eixo.set_xticks(SEMANAS)
    eixo.set_xlabel("Semana")
    eixo.set_ylabel("Horas")
    eixo.set_title(f"Carga x capacidade - {centro['codigo']} "
                   f"{centro['descricao']}")
    eixo.grid(axis="y", alpha=0.3)
    eixo.legend(handles=[
        Patch(color=COR_NORMAL, label="Carga dentro da capacidade"),
        Patch(color=COR_ALERTA, label="Carga em sobrecarga"),
        Line2D([0], [0], color="black", linestyle="--",
               label=f"Capacidade ({centro['capacidade']:g} h/semana)"),
    ])
    return figura


def figura_previsao(resultado, figura):
    """Historico de demanda real + previsao das 8 semanas (bonus - IA)."""
    exigir_matplotlib()
    historico = resultado["historico"]
    previsao = resultado["previsao"]
    anteriores = list(range(1 - len(historico), 1))
    futuras = list(range(1, len(previsao) + 1))

    eixo = figura.subplots()
    eixo.plot(anteriores, historico, marker="o", color=COR_NORMAL,
              label="Demanda real (historico)")
    eixo.plot([0] + futuras, [historico[-1]] + previsao, marker="s",
              linestyle="--", color=COR_OC,
              label=f"Previsao ({resultado['rotulo']})")
    eixo.fill_between(futuras, resultado["faixa_inferior"],
                      resultado["faixa_superior"], color=COR_OC, alpha=0.2,
                      label="Faixa de ~80%")
    eixo.axvline(0.5, color="gray", linestyle=":")
    codigo = resultado.get("codigo", "")
    eixo.set_title(f"Previsao de demanda - {codigo}".rstrip(" -"))
    eixo.set_xlabel("Semana (0 = ultima semana com demanda real)")
    eixo.set_ylabel("Unidades")
    eixo.set_ylim(bottom=0)
    eixo.grid(alpha=0.3)
    eixo.legend(loc="upper left")
    return figura


def grafico_posicao_estoque(dados, mostrar=True):
    """Posicao de estoque: saldo atual x estoque de seguranca (barras)."""
    return _gerar_arquivo(
        lambda figura: figura_posicao_estoque(dados, figura),
        (12, 6), "grafico_posicao_estoque.png", mostrar)


def grafico_estoque_projetado(dados, codigo, mostrar=True):
    """Estoque projetado de um item nas 8 semanas do MRP."""
    codigo = obter_item(dados, codigo)["codigo"]
    return _gerar_arquivo(
        lambda figura: figura_estoque_projetado(dados, codigo, figura),
        (10, 5), f"grafico_estoque_projetado_{codigo}.png", mostrar)


def grafico_ordens_por_semana(dados, mostrar=True):
    """OPs e OCs por semana de entrega (barras empilhadas)."""
    return _gerar_arquivo(
        lambda figura: figura_ordens_por_semana(dados, figura),
        (10, 5), "grafico_ordens_por_semana.png", mostrar)


def grafico_carga_capacidade(dados, codigo_centro, mostrar=True):
    """Carga x capacidade de um centro, destacando sobrecargas."""
    codigo = capacidade.obter_centro(dados, codigo_centro)["codigo"]
    return _gerar_arquivo(
        lambda figura: figura_carga_capacidade(dados, codigo, figura),
        (10, 5), f"grafico_carga_capacidade_{codigo}.png", mostrar)


def grafico_previsao(resultado, mostrar=True):
    """Historico + previsao de demanda de um PA."""
    codigo = resultado.get("codigo", "PA")
    return _gerar_arquivo(
        lambda figura: figura_previsao(resultado, figura),
        (10, 5), f"grafico_previsao_{codigo}.png", mostrar)
