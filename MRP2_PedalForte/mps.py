from persistencia import carregar_json, salvar_json
from utils import ler_float_positivo, ler_int_positivo


def exibir_mps() -> None:
    itens = carregar_json("itens")
    mps = carregar_json("mps")

    produtos_pa = sorted([cod for cod, d in itens.items() if d["tipo"] == "PA"])
    if not produtos_pa:
        print("Nenhum Produto Acabado (PA) cadastrado.")
        return

    print("\n" + "=" * 99)
    cabecalho_sem = " ".join([f"{f'S{s}':>6}" for s in range(1, 9)])
    print(f"{'PRODUTO':<8} {'DESCRIÇÃO':<26} {cabecalho_sem} {'TOTAL':>7}")
    print("-" * 99)

    for cod in produtos_pa:
        demandas = mps.get(cod, [0.0] * 8)
        demandas_8 = (list(demandas) + [0.0] * 8)[:8]
        valores_str = " ".join([f"{v:>6g}" for v in demandas_8])
        total = sum(demandas_8)
        print(f"{cod:<8} {itens[cod]['descricao']:<26} {valores_str} {total:>7g}")

    print("=" * 99)


def cadastrar_alterar_mps() -> None:
    itens = carregar_json("itens")
    mps = carregar_json("mps")

    exibir_mps()
    codigo = input("\nCódigo do Produto Acabado (ex.: PA-001): ").strip().upper()

    if codigo not in itens:
        print("ERRO: Produto não encontrado.")
        return
    if itens[codigo]["tipo"] != "PA":
        print("ERRO: O MPS aplica-se apenas a Produtos Acabados (PA).")
        return

    atual = (list(mps.get(codigo, [0.0] * 8)) + [0.0] * 8)[:8]
    print(f"\nEditando MPS de {codigo} - {itens[codigo]['descricao']}")
    print("1. Preencher todas as 8 semanas")
    print("2. Alterar uma semana específica (1 a 8)")
    modo = input("Escolha uma opção: ").strip()

    if modo == "1":
        novas_demandas = []
        for sem in range(1, 9):
            qtd = ler_float_positivo(
                f"Demanda Semana {sem} [atual {atual[sem - 1]:g}]: ",
                permitir_zero=True,
            )
            novas_demandas.append(qtd)
        mps[codigo] = novas_demandas
    elif modo == "2":
        while True:
            sem = ler_int_positivo("Número da semana (1 a 8): ")
            if 1 <= sem <= 8:
                break
            print("ERRO: A semana deve estar entre 1 e 8.")
        qtd = ler_float_positivo(
            f"Nova demanda para Semana {sem} [atual {atual[sem - 1]:g}]: ",
            permitir_zero=True,
        )
        atual[sem - 1] = qtd
        mps[codigo] = atual
    else:
        print("Opção inválida.")
        return

    salvar_json("mps", mps)
    print(f"MPS de {codigo} atualizado com sucesso!")