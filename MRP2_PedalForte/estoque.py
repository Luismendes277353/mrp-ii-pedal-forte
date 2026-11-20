from persistencia import (
    carregar_json,
    carregar_movimentos_csv,
    registrar_movimento_csv,
    salvar_json,
)
from utils import ler_float_positivo, ler_texto_nao_vazio, obter_data_atual


def registrar_movimentacao(
    codigo: str,
    tipo: str,
    quantidade: float,
    documento: str,
    data: str | None = None,
) -> tuple[bool, str]:
    itens = carregar_json("itens")
    estoque = carregar_json("estoque")

    codigo = codigo.strip().upper()
    if codigo not in itens:
        return False, f"ERRO: Item {codigo} não cadastrado."

    tipo_norm = tipo.strip().upper()
    if tipo_norm not in ("ENTRADA", "SAIDA", "AJUSTE"):
        return False, "ERRO: Tipo de movimentação inválido."

    saldo_atual = float(estoque.get(codigo, 0.0))
    unidade = itens[codigo]["unidade"]

    if tipo_norm == "ENTRADA":
        if quantidade <= 0:
            return False, "ERRO: Quantidade de entrada deve ser maior que zero."
        delta = quantidade
    elif tipo_norm == "SAIDA":
        if quantidade <= 0:
            return False, "ERRO: Quantidade de saída deve ser maior que zero."
        if quantidade > saldo_atual:
            return (
                False,
                f"ERRO: saldo insuficiente (saldo atual: {saldo_atual:g} {unidade}). "
                "Operacao cancelada.",
            )
        delta = -quantidade
    else:
        if quantidade == 0:
            return False, "ERRO: O valor do ajuste não pode ser zero."
        if saldo_atual + quantidade < 0:
            return (
                False,
                f"ERRO [RN02]: Ajuste deixaria o saldo negativo "
                f"(saldo atual: {saldo_atual:g} {unidade}). Operacao cancelada.",
            )
        delta = quantidade

    novo_saldo = round(saldo_atual + delta, 4)
    estoque[codigo] = novo_saldo
    salvar_json("estoque", estoque)

    data_mov = data if data else obter_data_atual()
    registrar_movimento_csv(data_mov, codigo, tipo_norm, delta, novo_saldo, documento)

    return True, f"Movimentação registrada. Novo saldo de {codigo}: {novo_saldo:g} {unidade}."


def _ler_float_ajuste(mensagem: str) -> float:
    while True:
        entrada = input(mensagem).strip().replace(",", ".")
        try:
            valor = float(entrada)
            if valor != 0:
                return valor
            print("ERRO: O ajuste não pode ser zero.")
        except ValueError:
            print("ERRO: Informe um número válido (ex.: 5 ou -2).")


def movimentar_estoque() -> None:
    itens = carregar_json("itens")
    codigo = input("Código do item (ex.: MP-202): ").strip().upper()

    if codigo not in itens:
        print("ERRO: Item não encontrado.")
        return

    mapa_tipos = {"E": "ENTRADA", "S": "SAIDA", "A": "AJUSTE"}
    while True:
        opcao = input("Tipo [E]ntrada [S]aida [A]juste: ").strip().upper()
        if opcao in mapa_tipos:
            tipo = mapa_tipos[opcao]
            break
        print("ERRO: Escolha E, S ou A.")

    if tipo == "AJUSTE":
        quantidade = _ler_float_ajuste("Quantidade do ajuste (+ para sobra, - para perda): ")
    else:
        quantidade = ler_float_positivo("Quantidade: ")

    documento = ler_texto_nao_vazio("Documento / Motivo (ex.: NF 4521, Inventario): ")
    data_in = input(f"Data [{obter_data_atual()}]: ").strip()
    data = data_in if data_in else obter_data_atual()

    sucesso, mensagem = registrar_movimentacao(codigo, tipo, quantidade, documento, data)
    print(mensagem)

    if not sucesso:
        consultar_kardex(codigo)


def consultar_kardex(codigo: str | None = None) -> None:
    itens = carregar_json("itens")
    estoque = carregar_json("estoque")

    if codigo is None:
        codigo = input("Código do item para consulta de Kardex: ").strip().upper()

    if codigo not in itens:
        print("ERRO: Item não encontrado.")
        return

    item = itens[codigo]
    saldo_atual = float(estoque.get(codigo, 0.0))
    est_seg = float(item["estoque_seguranca"])
    unidade = item["unidade"]

    movimentos = [m for m in carregar_movimentos_csv() if m["codigo"] == codigo]

    print(f"\nKARDEX - {codigo} {item['descricao']} ({unidade})")
    print(f"{'Data':<12} {'Tipo':<10} {'Qtde':>8} {'Saldo':>8}  {'Documento'}")
    print("-" * 68)

    if not movimentos:
        print("Nenhuma movimentação registrada para este item.")
    else:
        for mov in movimentos:
            qtd = float(mov["quantidade"])
            saldo = float(mov["saldo_apos"])
            qtd_fmt = f"{qtd:+g}"
            print(
                f"{mov['data']:<12} {mov['tipo']:<10} {qtd_fmt:>8} "
                f"{saldo:>8g}  {mov['documento']}"
            )

    print("-" * 68)
    print(f"Saldo atual: {saldo_atual:g} {unidade} | Estoque de seguranca: {est_seg:g} {unidade}")

    if saldo_atual < est_seg:
        print(
            f"ALERTA: saldo ({saldo_atual:g} {unidade}) abaixo do estoque "
            f"de seguranca ({est_seg:g} {unidade})."
        )


def exibir_posicao_estoque() -> None:
    itens = carregar_json("itens")
    estoque = carregar_json("estoque")

    print("\n" + "=" * 78)
    print(
        f"{'CÓDIGO':<8} {'DESCRIÇÃO':<28} {'UN':<4} "
        f"{'SALDO':>9} {'EST.SEG':>9} {'STATUS':<14}"
    )
    print("-" * 78)
    for cod in sorted(itens.keys()):
        item = itens[cod]
        saldo = float(estoque.get(cod, 0.0))
        es = float(item["estoque_seguranca"])
        status = "ABAIXO ES!" if saldo < es else "OK"
        print(
            f"{cod:<8} {item['descricao']:<28} {item['unidade']:<4} "
            f"{saldo:>9.1f} {es:>9.1f} {status:<14}"
        )
    print("=" * 78)