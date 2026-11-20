from estoque import registrar_movimentacao
from persistencia import carregar_json, salvar_json
from utils import obter_data_atual


def _buscar_ordem(ordens: list[dict], numero: str) -> dict | None:
    numero_norm = numero.strip().upper()
    for ordem in ordens:
        if ordem["numero"].upper() == numero_norm:
            return ordem
    return None


def listar_ordens() -> None:
    ordens = carregar_json("ordens", padrao=[])
    if not ordens:
        print("\nNenhuma ordem cadastrada. Execute o MRP primeiro.")
        return

    print(f"\nORDENS PLANEJADAS E EM CARTEIRA - consulta em {obter_data_atual()}")
    print(
        f"{'Ordem':<9} {'Tipo':<6} {'Item':<9} {'Qtde':>8} "
        f"{'Liberar':>8} {'Entregar':>9}  {'Status'}"
    )
    print("-" * 68)

    atrasadas = 0
    for ordem in ordens:
        lib_str = f"S{ordem['semana_liberacao']}"
        ent_str = f"S{ordem['semana_entrega']}"
        status = ordem["status"]
        if status == "ATRASADA":
            atrasadas += 1
        print(
            f"{ordem['numero']:<9} {ordem['tipo']:<6} {ordem['item']:<9} "
            f"{ordem['quantidade']:>8g} {lib_str:>8} {ent_str:>9}  {status}"
        )

    print("-" * 68)
    if atrasadas > 0:
        print(
            f"{atrasadas} mensagem(ns) de excecao: "
            "ordens com liberacao antes da semana 1."
        )


def firmar_ordem() -> None:
    ordens = carregar_json("ordens", padrao=[])
    numero = input("Número da ordem para FIRMAR (ex.: OP-0002): ").strip().upper()
    ordem = _buscar_ordem(ordens, numero)

    if not ordem:
        print("ERRO: Ordem não encontrada.")
        return

    if ordem["status"] not in ("PLANEJADA", "ATRASADA"):
        print(
            f"ERRO [RF10]: Apenas ordens PLANEJADA ou ATRASADA podem ser firmadas "
            f"(status atual: {ordem['status']})."
        )
        return

    ordem["status"] = "FIRME"
    salvar_json("ordens", ordens)
    print(f"Ordem {ordem['numero']} ({ordem['item']}) alterada para FIRME.")


def liberar_ordem() -> None:
    ordens = carregar_json("ordens", padrao=[])
    numero = input("Número da ordem para LIBERAR (ex.: OP-0001): ").strip().upper()
    ordem = _buscar_ordem(ordens, numero)

    if not ordem:
        print("ERRO: Ordem não encontrada.")
        return

    if ordem["status"] != "FIRME":
        print(
            f"ERRO [RF10]: A ordem deve estar FIRME antes de ser liberada "
            f"(status atual: {ordem['status']})."
        )
        return

    ordem["status"] = "LIBERADA"
    salvar_json("ordens", ordens)
    print(f"Ordem {ordem['numero']} ({ordem['item']}) alterada para LIBERADA.")


def apontar_ou_encerrar_ordem() -> None:
    ordens = carregar_json("ordens", padrao=[])
    itens = carregar_json("itens")
    estrutura = carregar_json("estrutura")
    estoque = carregar_json("estoque")

    numero = input("Número da ordem LIBERADA para apontar/encerrar: ").strip().upper()
    ordem = _buscar_ordem(ordens, numero)

    if not ordem:
        print("ERRO: Ordem não encontrada.")
        return

    if ordem["status"] != "LIBERADA":
        print(
            f"ERRO [RF11]: Apenas ordens LIBERADAS podem ser apontadas/encerradas "
            f"(status atual: {ordem['status']})."
        )
        return

    item_cod = ordem["item"]
    qtd_ordem = float(ordem["quantidade"])

    if ordem["tipo"] == "OC":
        sucesso, msg = registrar_movimentacao(
            item_cod, "ENTRADA", qtd_ordem, f"Recebimento {ordem['numero']}"
        )
        if sucesso:
            ordem["status"] = "ENCERRADA"
            salvar_json("ordens", ordens)
            print(f"Ordem de Compra {ordem['numero']} encerrada! {msg}")
        else:
            print(msg)
        return

    componentes = estrutura.get(item_cod, [])
    if not componentes:
        print(f"ERRO: O item {item_cod} não possui estrutura (BOM) cadastrada.")
        return

    consumos: dict[str, float] = {}
    for comp_info in componentes:
        comp_cod = comp_info["componente"]
        qtd_nec = round(qtd_ordem * float(comp_info["quantidade"]), 4)
        consumos[comp_cod] = consumos.get(comp_cod, 0.0) + qtd_nec

    faltantes = []
    for comp_cod, qtd_nec in consumos.items():
        saldo_disp = float(estoque.get(comp_cod, 0.0))
        if saldo_disp < qtd_nec:
            un = itens.get(comp_cod, {}).get("unidade", "un")
            faltantes.append(
                f"  - {comp_cod} ({itens[comp_cod]['descricao']}): "
                f"necessário {qtd_nec:g} {un}, disponível {saldo_disp:g} {un}"
            )

    if faltantes:
        print(f"ERRO [RF11/RN02]: Apontamento de {ordem['numero']} rejeitado por falta de componente:")
        for linha in faltantes:
            print(linha)
        return

    data_hoje = obter_data_atual()
    for comp_cod, qtd_nec in consumos.items():
        registrar_movimentacao(
            comp_cod, "SAIDA", qtd_nec, f"{ordem['numero']} ({item_cod})", data_hoje
        )

    registrar_movimentacao(
        item_cod, "ENTRADA", qtd_ordem, f"{ordem['numero']}", data_hoje
    )

    ordem["status"] = "ENCERRADA"
    salvar_json("ordens", ordens)
    print(
        f"Apontamento concluído! {qtd_ordem:g} {itens[item_cod]['unidade']} de "
        f"{item_cod} produzidos e ordem {ordem['numero']} ENCERRADA."
    )


def gerenciar_ordens() -> None:
    while True:
        listar_ordens()
        print("\n[F] Firmar  [L] Liberar  [A] Apontar producao / Encerrar  [V] Voltar")
        acao = input("Escolha uma acao: ").strip().upper()

        match acao:
            case "F":
                firmar_ordem()
            case "L":
                liberar_ordem()
            case "A":
                apontar_ou_encerrar_ordem()
            case "V":
                break
            case _:
                print("Opção inválida.")