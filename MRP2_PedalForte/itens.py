from persistencia import carregar_json, salvar_json
from utils import (
    ler_float_positivo,
    ler_int_positivo,
    ler_texto_nao_vazio,
    validar_codigo_item,
)


def cadastrar_item() -> None:
    itens = carregar_json("itens")
    estoque = carregar_json("estoque")

    while True:
        codigo = input("Código do item (ex.: PA-003, SA-030, MP-400): ").strip().upper()
        if not validar_codigo_item(codigo):
            print("ERRO [RN01]: Código deve seguir o padrão PA-000, SA-000 ou MP-000.")
            continue
        if codigo in itens:
            print(f"ERRO [RN01]: O código {codigo} já está cadastrado.")
            return
        break

    tipo = codigo.split("-")[0]
    descricao = ler_texto_nao_vazio("Descrição do item: ")
    unidade = ler_texto_nao_vazio("Unidade de medida (ex.: un, m, L, kg): ")

    if tipo == "MP":
        custo_unitario = ler_float_positivo("Custo unitário de compra (R$): ")
    else:
        print("Nota: Itens PA e SA têm custo padrão calculado pela BOM + Roteiro.")
        custo_unitario = 0.0

    lead_time = ler_int_positivo("Lead time (semanas): ", permitir_zero=False)
    estoque_seguranca = ler_float_positivo("Estoque de segurança: ", permitir_zero=True)
    lote_minimo = ler_float_positivo("Lote mínimo: ", permitir_zero=False)

    itens[codigo] = {
        "descricao": descricao,
        "tipo": tipo,
        "unidade": unidade,
        "custo_unitario": custo_unitario,
        "lead_time": lead_time,
        "estoque_seguranca": estoque_seguranca,
        "lote_minimo": lote_minimo,
    }
    estoque[codigo] = 0.0

    salvar_json("itens", itens)
    salvar_json("estoque", estoque)
    print(f"Item {codigo} - {descricao} cadastrado com sucesso!")


def listar_itens() -> None:
    itens = carregar_json("itens")
    if not itens:
        print("Nenhum item cadastrado.")
        return

    print("\n" + "=" * 88)
    print(
        f"{'CÓDIGO':<8} {'TIPO':<5} {'DESCRIÇÃO':<28} {'UN':<4} "
        f"{'CUSTO(R$)':>10} {'LT':>4} {'EST.SEG':>8} {'LOTE MIN':>9}"
    )
    print("-" * 88)
    for codigo in sorted(itens.keys()):
        dados = itens[codigo]
        print(
            f"{codigo:<8} {dados['tipo']:<5} {dados['descricao']:<28} "
            f"{dados['unidade']:<4} {dados['custo_unitario']:>10.2f} "
            f"{dados['lead_time']:>4} {dados['estoque_seguranca']:>8.1f} "
            f"{dados['lote_minimo']:>9.1f}"
        )
    print("=" * 88)


def alterar_item() -> None:
    itens = carregar_json("itens")
    codigo = input("Informe o código do item a alterar: ").strip().upper()

    if codigo not in itens:
        print("ERRO: Item não encontrado.")
        return

    item = itens[codigo]
    print(f"\nEditando {codigo} - {item['descricao']} (Enter mantém o valor atual):")

    nova_desc = input(f"Descrição [{item['descricao']}]: ").strip()
    if nova_desc:
        item["descricao"] = nova_desc

    nova_un = input(f"Unidade [{item['unidade']}]: ").strip()
    if nova_un:
        item["unidade"] = nova_un

    if item["tipo"] == "MP":
        novo_custo = input(f"Custo unitário [{item['custo_unitario']:.2f}]: ").strip()
        if novo_custo:
            try:
                valor = float(novo_custo.replace(",", "."))
                if valor > 0:
                    item["custo_unitario"] = valor
            except ValueError:
                print("Aviso: Custo inválido ignorado.")

    novo_lt = input(f"Lead time (sem) [{item['lead_time']}]: ").strip()
    if novo_lt.isdigit() and int(novo_lt) > 0:
        item["lead_time"] = int(novo_lt)

    novo_es = input(f"Estoque de segurança [{item['estoque_seguranca']}]: ").strip()
    if novo_es:
        try:
            valor = float(novo_es.replace(",", "."))
            if valor >= 0:
                item["estoque_seguranca"] = valor
        except ValueError:
            print("Aviso: Estoque de segurança inválido ignorado.")

    novo_lote = input(f"Lote mínimo [{item['lote_minimo']}]: ").strip()
    if novo_lote:
        try:
            valor = float(novo_lote.replace(",", "."))
            if valor > 0:
                item["lote_minimo"] = valor
        except ValueError:
            print("Aviso: Lote mínimo inválido ignorado.")

    salvar_json("itens", itens)
    print(f"Item {codigo} atualizado com sucesso!")