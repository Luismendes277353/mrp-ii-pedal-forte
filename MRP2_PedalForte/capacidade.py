import re
from persistencia import carregar_json, salvar_json
from utils import ler_float_positivo, ler_texto_nao_vazio


def cadastrar_centro_trabalho() -> None:
    centros = carregar_json("centros")

    while True:
        codigo = input("Código do centro (ex.: CT-04): ").strip().upper()
        if re.match(r"^CT-\d{2}$", codigo):
            break
        print("ERRO: Use o formato CT-00 (ex.: CT-01).")

    descricao = ler_texto_nao_vazio("Descrição do centro de trabalho: ")
    capacidade = ler_float_positivo("Capacidade disponível (horas/semana): ")
    custo_hora = ler_float_positivo("Custo-hora de mão de obra (R$/h): ")

    centros[codigo] = {
        "descricao": descricao,
        "capacidade_semanal": capacidade,
        "custo_hora": custo_hora,
    }
    salvar_json("centros", centros)
    print(f"Centro {codigo} - {descricao} salvo com sucesso!")


def listar_centros_trabalho() -> None:
    centros = carregar_json("centros")
    if not centros:
        print("Nenhum centro de trabalho cadastrado.")
        return

    print("\n" + "=" * 72)
    print(f"{'CENTRO':<8} {'DESCRIÇÃO':<32} {'CAPAC. (h/sem)':>15} {'CUSTO/H (R$)':>14}")
    print("-" * 72)
    for cod in sorted(centros.keys()):
        ct = centros[cod]
        print(
            f"{cod:<8} {ct['descricao']:<32} "
            f"{ct['capacidade_semanal']:>15.1f} {ct['custo_hora']:>14.2f}"
        )
    print("=" * 72)


def cadastrar_roteiro() -> None:
    itens = carregar_json("itens")
    centros = carregar_json("centros")
    roteiros = carregar_json("roteiros")

    item_cod = input("Código do item fabricado (PA ou SA): ").strip().upper()
    if item_cod not in itens:
        print("ERRO: Item não encontrado.")
        return
    if itens[item_cod]["tipo"] == "MP":
        print("ERRO [RN01]: Matéria-prima (MP) é comprada e não possui roteiro de fabricação.")
        return

    centro_cod = input("Código do centro de trabalho (ex.: CT-03): ").strip().upper()
    if centro_cod not in centros:
        print("ERRO: Centro de trabalho não encontrado.")
        return

    tempo = ler_float_positivo("Tempo de fabricação por unidade (em horas, ex.: 0.5): ")

    roteiros[item_cod] = {"centro": centro_cod, "tempo_unitario": tempo}
    salvar_json("roteiros", roteiros)
    print(f"Roteiro de {item_cod} vinculado ao centro {centro_cod} ({tempo} h/un).")


def listar_roteiros() -> None:
    roteiros = carregar_json("roteiros")
    itens = carregar_json("itens")
    centros = carregar_json("centros")

    if not roteiros:
        print("Nenhum roteiro cadastrado.")
        return

    print("\n" + "=" * 76)
    print(f"{'ITEM':<8} {'DESCRIÇÃO':<28} {'CENTRO':<8} {'DESCRIÇÃO CT':<20} {'TEMPO(h)':>9}")
    print("-" * 76)
    for item_cod in sorted(roteiros.keys()):
        rot = roteiros[item_cod]
        desc_item = itens.get(item_cod, {}).get("descricao", "N/A")
        desc_ct = centros.get(rot["centro"], {}).get("descricao", "N/A")
        print(
            f"{item_cod:<8} {desc_item:<28} {rot['centro']:<8} "
            f"{desc_ct:<20} {rot['tempo_unitario']:>9.2f}"
        )
    print("=" * 76)


def calcular_carga_semanal_centro(codigo_centro: str) -> dict[int, float]:
    ordens = carregar_json("ordens", padrao=[])
    roteiros = carregar_json("roteiros")

    carga = {semana: 0.0 for semana in range(1, 9)}

    for ordem in ordens:
        if ordem["tipo"] != "OP" or ordem["status"] != "LIBERADA":
            continue

        item_cod = ordem["item"]
        roteiro = roteiros.get(item_cod)
        if not roteiro or roteiro["centro"] != codigo_centro:
            continue

        semana = ordem["semana_liberacao"]
        # Caso a OP liberada tenha sido planejada para S0 (atrasada), aloca na S1
        semana_efetiva = 1 if semana < 1 else semana
        if 1 <= semana_efetiva <= 8:
            carga[semana_efetiva] += ordem["quantidade"] * roteiro["tempo_unitario"]

    return carga


def exibir_crp() -> None:
    centros = carregar_json("centros")
    if not centros:
        print("Nenhum centro de trabalho cadastrado.")
        return

    listar_centros_trabalho()
    codigo = input("Código do centro para análise CRP (ex.: CT-03): ").strip().upper()
    if codigo not in centros:
        print("ERRO: Centro de trabalho não encontrado.")
        return

    ct = centros[codigo]
    capacidade = ct["capacidade_semanal"]
    carga_semanal = calcular_carga_semanal_centro(codigo)

    print(f"\nCARGA x CAPACIDADE - {codigo} {ct['descricao']} ({capacidade:.1f} h/semana)")
    print(f"{'Sem':<4} {'Carga(h)':>9} {'Uso(%)':>7}  {'Gráfico'}")

    semanas_sobrecarga = []
    for sem in range(1, 9):
        carga = carga_semanal[sem]
        uso_pct = (carga / capacidade * 100.0) if capacidade > 0 else 0.0
        blocos = "#" * int(round(uso_pct / 10.0))
        alerta = " SOBRECARGA" if carga > capacidade else ""
        if alerta:
            semanas_sobrecarga.append(str(sem))
        print(f"{sem:<4} {carga:>9.1f} {uso_pct:>6.0f}%  {blocos}{alerta}")

    if semanas_sobrecarga:
        lista_sem = " e ".join(semanas_sobrecarga)
        print(f"\nSugestao: antecipar OPs ou programar hora extra nas semanas {lista_sem}.")
    else:
        print("\nCapacidade dentro do limite em todas as 8 semanas.")