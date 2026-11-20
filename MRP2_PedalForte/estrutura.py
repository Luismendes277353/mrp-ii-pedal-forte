from persistencia import carregar_json, salvar_json
from utils import ler_float_positivo


def cadastrar_componente_bom() -> None:
    itens = carregar_json("itens")
    estrutura = carregar_json("estrutura")

    pai = input("Código do item PAI (PA ou SA): ").strip().upper()
    if pai not in itens:
        print("ERRO: Item pai não encontrado.")
        return

    tipo_pai = itens[pai]["tipo"]
    if tipo_pai == "MP":
        print("ERRO [RN03]: Matéria-prima (MP) não pode possuir estrutura.")
        return

    comp = input("Código do item COMPONENTE: ").strip().upper()
    if comp not in itens:
        print("ERRO: Componente não encontrado.")
        return

    if comp == pai:
        print("ERRO [RN03]: Um item não pode ser componente de si mesmo.")
        return

    tipo_comp = itens[comp]["tipo"]

    if tipo_comp == "PA":
        print("ERRO [RN03]: Produto Acabado (PA) não pode ser componente de outro item.")
        return
    if tipo_pai == "SA" and tipo_comp != "MP":
        print("ERRO [RN03]: Semiacabado (SA) pode ter apenas Matéria-Prima (MP) como componente.")
        return

    quantidade = ler_float_positivo(
        f"Quantidade de {comp} ({itens[comp]['unidade']}) por unidade de {pai}: "
    )

    lista_comp = estrutura.setdefault(pai, [])
    for registro in lista_comp:
        if registro["componente"] == comp:
            registro["quantidade"] = quantidade
            salvar_json("estrutura", estrutura)
            print(f"Quantidade de {comp} em {pai} atualizada para {quantidade}.")
            return

    lista_comp.append({"componente": comp, "quantidade": quantidade})
    salvar_json("estrutura", estrutura)
    print(f"Componente {comp} adicionado à estrutura de {pai} com sucesso!")


def _explodir_recursivo(
    codigo: str,
    itens: dict,
    estrutura: dict,
    nivel: int = 0,
    prefixo: str = "",
    niveis_mapa: dict[int, list[str]] | None = None,
) -> None:
    if niveis_mapa is None:
        niveis_mapa = {}

    filhos = estrutura.get(codigo, [])
    total_filhos = len(filhos)

    for indice, item_filho in enumerate(filhos):
        comp = item_filho["componente"]
        qtd = item_filho["quantidade"]
        ultimo = indice == total_filhos - 1

        conector = "└── " if ultimo else "├── "
        desc = itens[comp]["descricao"]
        un = itens[comp]["unidade"]
        qtd_str = f"{qtd:g}".replace(".", ",")

        rotulo = f"{comp} {desc}"
        pontos = "." * max(2, 34 - len(rotulo))
        print(f"{prefixo}{conector}{rotulo} {pontos} {qtd_str} {un}")

        niveis_mapa.setdefault(nivel + 1, [])
        if comp not in niveis_mapa[nivel + 1]:
            niveis_mapa[nivel + 1].append(comp)

        novo_prefixo = prefixo + ("    " if ultimo else "│   ")
        _explodir_recursivo(comp, itens, estrutura, nivel + 1, novo_prefixo, niveis_mapa)


def exibir_estrutura() -> None:
    itens = carregar_json("itens")
    estrutura = carregar_json("estrutura")

    codigo = input("Código do produto (ex.: PA-001): ").strip().upper()
    if codigo not in itens:
        print("ERRO: Item não encontrado.")
        return

    if itens[codigo]["tipo"] == "MP":
        print("ERRO [RN03]: Matéria-prima não possui estrutura.")
        return

    print(f"\n{codigo} {itens[codigo]['descricao']}")
    if codigo not in estrutura or not estrutura[codigo]:
        print("  (Nenhum componente cadastrado para este item)")
        return

    niveis_mapa: dict[int, list[str]] = {0: [codigo]}
    _explodir_recursivo(codigo, itens, estrutura, nivel=0, niveis_mapa=niveis_mapa)

    n0 = ", ".join(niveis_mapa.get(0, []))
    n1 = ", ".join(niveis_mapa.get(1, []))
    resumo = f"Niveis: 0 = {n0} | 1 = {n1}"
    if 2 in niveis_mapa:
        resumo += " | 2 = demais"
    print(resumo)