from persistencia import carregar_json, salvar_json


def calcular_custo_unitario_recursivo(
    codigo: str,
    itens: dict,
    estrutura: dict,
    centros: dict,
    roteiros: dict,
) -> float:
    item = itens[codigo]

    if item["tipo"] == "MP":
        return float(item["custo_unitario"])

    custo_materiais = 0.0
    for filho in estrutura.get(codigo, []):
        comp = filho["componente"]
        qtd = filho["quantidade"]
        custo_comp = calcular_custo_unitario_recursivo(
            comp, itens, estrutura, centros, roteiros
        )
        custo_materiais += qtd * custo_comp

    custo_mao_obra = 0.0
    roteiro = roteiros.get(codigo)
    if roteiro:
        ct = centros.get(roteiro["centro"])
        if ct:
            custo_mao_obra = roteiro["tempo_unitario"] * ct["custo_hora"]

    return round(custo_materiais + custo_mao_obra, 2)


def atualizar_todos_custos_padrao() -> dict[str, float]:
    itens = carregar_json("itens")
    estrutura = carregar_json("estrutura")
    centros = carregar_json("centros")
    roteiros = carregar_json("roteiros")

    for codigo, dados in itens.items():
        if dados["tipo"] in ("PA", "SA"):
            dados["custo_unitario"] = calcular_custo_unitario_recursivo(
                codigo, itens, estrutura, centros, roteiros
            )

    salvar_json("itens", itens)
    return {cod: d["custo_unitario"] for cod, d in itens.items()}


def exibir_custo_padrao() -> None:
    itens = carregar_json("itens")
    estrutura = carregar_json("estrutura")
    centros = carregar_json("centros")
    roteiros = carregar_json("roteiros")

    codigo = input("Código do produto fabricado (ex.: PA-001): ").strip().upper()
    if codigo not in itens:
        print("ERRO: Item não encontrado.")
        return

    if itens[codigo]["tipo"] == "MP":
        print(
            f"{codigo} é Matéria-Prima. Custo unitário de compra: "
            f"R$ {itens[codigo]['custo_unitario']:.2f}"
        )
        return

    print(f"\nCUSTO PADRAO - {codigo} {itens[codigo]['descricao']}")
    print(f"{'Item':<14} {'Descricao':<26} {'Qtde':>6} {'Custo un.':>10} {'Total':>10}")
    print("-" * 70)

    total_geral = 0.0
    for filho in estrutura.get(codigo, []):
        comp = filho["componente"]
        qtd = filho["quantidade"]
        custo_un = calcular_custo_unitario_recursivo(
            comp, itens, estrutura, centros, roteiros
        )
        subtotal = qtd * custo_un
        total_geral += subtotal
        qtd_fmt = f"{qtd:g}".replace(".", ",")
        print(
            f"{comp:<14} {itens[comp]['descricao']:<26} "
            f"{qtd_fmt:>6} {custo_un:>10.2f} {subtotal:>10.2f}"
        )

    roteiro = roteiros.get(codigo)
    if roteiro and roteiro["centro"] in centros:
        ct_cod = roteiro["centro"]
        tempo = roteiro["tempo_unitario"]
        custo_h = centros[ct_cod]["custo_hora"]
        subtotal_mo = tempo * custo_h
        total_geral += subtotal_mo
        tempo_fmt = f"{tempo:g} h".replace(".", ",")
        print(
            f"{'Mao de obra':<14} {ct_cod:<26} "
            f"{tempo_fmt:>6} {custo_h:>10.2f} {subtotal_mo:>10.2f}"
        )

    print("-" * 70)
    print(f"{'CUSTO PADRAO TOTAL':<58} R$ {total_geral:>8.2f}")
    atualizar_todos_custos_padrao()