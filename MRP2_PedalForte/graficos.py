import os
import matplotlib.pyplot as plt
from capacidade import calcular_carga_semanal_centro
from mrp import calcular_mrp
from persistencia import carregar_json

PASTA_GRAFICOS = "docs"


def _exibir_e_salvar(caminho: str) -> None:
    os.makedirs(PASTA_GRAFICOS, exist_ok=True)
    plt.tight_layout()
    plt.savefig(caminho, dpi=150)
    print(f"Gráfico salvo em: {caminho}")
    try:
        plt.show()
    except Exception:
        pass
    finally:
        plt.close()


def grafico_posicao_estoque() -> str:
    itens = carregar_json("itens")
    estoque = carregar_json("estoque")

    codigos = sorted(itens.keys())
    saldos = [float(estoque.get(c, 0.0)) for c in codigos]
    seguranca = [float(itens[c]["estoque_seguranca"]) for c in codigos]

    x = list(range(len(codigos)))
    largura = 0.38

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar([i - largura / 2 for i in x], saldos, width=largura, label="Saldo Atual", color="#1f77b4")
    ax.bar([i + largura / 2 for i in x], seguranca, width=largura, label="Estoque de Segurança", color="#ff7f0e")

    ax.set_title("Posição de Estoque: Saldo Atual x Estoque de Segurança")
    ax.set_xlabel("Itens Cadastrados")
    ax.set_ylabel("Quantidade (unidades diversas)")
    ax.set_xticks(x)
    ax.set_xticklabels(codigos, rotation=45, ha="right")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    caminho = os.path.join(PASTA_GRAFICOS, "grafico_posicao_estoque.png")
    _exibir_e_salvar(caminho)
    return caminho


def grafico_estoque_projetado_mrp(codigo: str | None = None) -> str | None:
    registros, _, _ = calcular_mrp(salvar_ordens=False)

    if codigo is None:
        codigo = input("Código do item para gráfico MRP (ex.: SA-020): ").strip().upper()

    if codigo not in registros:
        print("ERRO: Item não encontrado.")
        return None

    reg = registros[codigo]
    semanas = [f"S{s}" for s in range(1, 9)]
    ep = reg["estoque_projetado"]
    es = reg["estoque_seguranca"]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.plot(semanas, ep, marker="o", linewidth=2.5, color="#2ca02c", label="Estoque Projetado")
    ax.axhline(y=es, color="#d62728", linestyle="--", linewidth=2, label=f"Estoque de Segurança ({es:g})")

    for idx, valor in enumerate(ep):
        ax.annotate(f"{valor:g}", (semanas[idx], valor), textcoords="offset points", xytext=(0, 8), ha="center")

    ax.set_title(f"Estoque Projetado (8 Semanas) - {codigo} {reg['descricao']}")
    ax.set_xlabel("Horizonte de Planejamento")
    ax.set_ylabel("Quantidade")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.5)

    caminho = os.path.join(PASTA_GRAFICOS, f"grafico_mrp_{codigo}.png")
    _exibir_e_salvar(caminho)
    return caminho


def grafico_ordens_por_semana() -> str:
    ordens = carregar_json("ordens", padrao=[])

    semanas = list(range(1, 9))
    rotulos = [f"S{s}" for s in semanas]
    contagem_op = [0] * 8
    contagem_oc = [0] * 8

    for ordem in ordens:
        sem_ent = int(ordem["semana_entrega"])
        if 1 <= sem_ent <= 8:
            if ordem["tipo"] == "OP":
                contagem_op[sem_ent - 1] += 1
            elif ordem["tipo"] == "OC":
                contagem_oc[sem_ent - 1] += 1

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(rotulos, contagem_op, label="Ordens de Produção (OP)", color="#1f77b4")
    ax.bar(rotulos, contagem_oc, bottom=contagem_op, label="Ordens de Compra (OC)", color="#ff7f0e")

    ax.set_title("Ordens de Produção (OP) e Compra (OC) por Semana de Entrega")
    ax.set_xlabel("Semana de Entrega (Chegada)")
    ax.set_ylabel("Quantidade de Ordens")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    caminho = os.path.join(PASTA_GRAFICOS, "grafico_ordens_semana.png")
    _exibir_e_salvar(caminho)
    return caminho


def grafico_crp_centro(codigo_centro: str | None = None) -> str | None:
    centros = carregar_json("centros")
    if not centros:
        print("Nenhum centro de trabalho cadastrado.")
        return None

    if codigo_centro is None:
        codigo_centro = input("Código do centro de trabalho (ex.: CT-03): ").strip().upper()

    if codigo_centro not in centros:
        print("ERRO: Centro de trabalho não encontrado.")
        return None

    ct = centros[codigo_centro]
    capacidade = float(ct["capacidade_semanal"])
    carga_dict = calcular_carga_semanal_centro(codigo_centro)

    semanas = [f"S{s}" for s in range(1, 9)]
    cargas = [carga_dict[s] for s in range(1, 9)]
    cores = ["#d62728" if c > capacidade else "#1f77b4" for c in cargas]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(semanas, cargas, color=cores, label="Carga Planejada (Azul=Normal / Vermelho=Sobrecarga)")
    ax.axhline(
        y=capacidade,
        color="#2ca02c",
        linestyle="--",
        linewidth=2,
        label=f"Capacidade Máxima ({capacidade:.1f} h/sem)",
    )

    ax.set_title(f"Carga x Capacidade (CRP) - {codigo_centro} {ct['descricao']}")
    ax.set_xlabel("Semana")
    ax.set_ylabel("Horas")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    caminho = os.path.join(PASTA_GRAFICOS, f"grafico_crp_{codigo_centro}.png")
    _exibir_e_salvar(caminho)
    return caminho


def menu_graficos() -> None:
    while True:
        print("\n--- GRÁFICOS DE GESTÃO (MATPLOTLIB) ---")
        print("1. Posição de estoque (Saldo x Estoque de Segurança)")
        print("2. Estoque projetado no MRP (8 semanas)")
        print("3. Ordens de Produção (OP) e Compra (OC) por semana de entrega")
        print("4. Carga x Capacidade (CRP) de um centro de trabalho")
        print("0. Voltar")

        opcao = input("Escolha uma opção: ").strip()
        match opcao:
            case "1":
                grafico_posicao_estoque()
            case "2":
                grafico_estoque_projetado_mrp()
            case "3":
                grafico_ordens_por_semana()
            case "4":
                grafico_crp_centro()
            case "0":
                break
            case _:
                print("Opção inválida.")