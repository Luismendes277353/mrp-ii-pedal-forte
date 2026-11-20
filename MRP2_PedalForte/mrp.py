from persistencia import carregar_json, salvar_json
from utils import obter_data_atual


def _proximo_numero_ordem(ordens_existentes: list[dict], prefixo: str) -> int:
    maior = 0
    for ordem in ordens_existentes:
        num_str = ordem.get("numero", "")
        if num_str.startswith(f"{prefixo}-"):
            try:
                num = int(num_str.split("-")[1])
                if num > maior:
                    maior = num
            except ValueError:
                continue
    return maior + 1


def calcular_mrp(
    salvar_ordens: bool = True,
) -> tuple[dict[str, dict], list[dict], list[str]]:
    itens = carregar_json("itens")
    estrutura = carregar_json("estrutura")
    estoque = carregar_json("estoque")
    mps = carregar_json("mps")
    ordens_atuais = carregar_json("ordens", padrao=[])

    ordens_mantidas = [
        o for o in ordens_atuais if o.get("status") in ("FIRME", "LIBERADA", "ENCERRADA")
    ]

    seq_op = _proximo_numero_ordem(ordens_mantidas, "OP")
    seq_oc = _proximo_numero_ordem(ordens_mantidas, "OC")

    necessidade_bruta: dict[str, list[float]] = {
        cod: [0.0] * 8 for cod in itens
    }

    for cod, dados in itens.items():
        if dados["tipo"] == "PA":
            demanda_pa = (list(mps.get(cod, [0.0] * 8)) + [0.0] * 8)[:8]
            necessidade_bruta[cod] = [float(v) for v in demanda_pa]

    ordem_tipos = {"PA": 0, "SA": 1, "MP": 2}
    itens_ordenados = sorted(
        itens.keys(), key=lambda c: (ordem_tipos.get(itens[c]["tipo"], 9), c)
    )

    registros_mrp: dict[str, dict] = {}
    novas_ordens: list[dict] = []
    mensagens_excecao: list[str] = []

    for cod in itens_ordenados:
        item = itens[cod]
        tipo = item["tipo"]
        lead_time = int(item["lead_time"])
        est_seg = float(item["estoque_seguranca"])
        lote_min = float(item["lote_minimo"])
        estoque_inicial = float(estoque.get(cod, 0.0))

        nb = necessidade_bruta[cod]
        rp = [0.0] * 8
        ep = [0.0] * 8
        nl = [0.0] * 8
        rec_plan = [0.0] * 8
        lib_plan = [0.0] * 8

        for ordem in ordens_mantidas:
            if ordem["item"] == cod and ordem["status"] in ("FIRME", "LIBERADA"):
                sem_ent = int(ordem["semana_entrega"])
                idx_ent = 0 if sem_ent < 1 else sem_ent - 1
                if 0 <= idx_ent < 8:
                    rp[idx_ent] += float(ordem["quantidade"])

        ep_anterior = estoque_inicial

        for idx in range(8):
            semana_atual = idx + 1

            necessidade = nb[idx] + est_seg - (ep_anterior + rp[idx])
            nl[idx] = round(max(0.0, necessidade), 4)

            if nl[idx] > 0:
                rec_plan[idx] = max(nl[idx], lote_min)
            else:
                rec_plan[idx] = 0.0

            ep[idx] = round(ep_anterior + rp[idx] + rec_plan[idx] - nb[idx], 4)
            ep_anterior = ep[idx]

            if rec_plan[idx] > 0:
                sem_liberacao = semana_atual - lead_time
                if sem_liberacao >= 1:
                    lib_plan[sem_liberacao - 1] += rec_plan[idx]
                    status_ordem = "PLANEJADA"
                else:
                    status_ordem = "ATRASADA"

                tipo_ordem = "OP" if tipo in ("PA", "SA") else "OC"
                if tipo_ordem == "OP":
                    numero_ordem = f"OP-{seq_op:04d}"
                    seq_op += 1
                else:
                    numero_ordem = f"OC-{seq_oc:04d}"
                    seq_oc += 1

                ordem_gerada = {
                    "numero": numero_ordem,
                    "tipo": tipo_ordem,
                    "item": cod,
                    "quantidade": rec_plan[idx],
                    "semana_liberacao": sem_liberacao,
                    "semana_entrega": semana_atual,
                    "status": status_ordem,
                }
                novas_ordens.append(ordem_gerada)

                if status_ordem == "ATRASADA":
                    mensagens_excecao.append(
                        f"EXCECAO [RN07]: {numero_ordem} ({cod}) com liberacao na "
                        f"S{sem_liberacao} (antes da S1) para entrega na S{semana_atual}."
                    )

                idx_demanda_filho = 0 if sem_liberacao < 1 else sem_liberacao - 1
                if idx_demanda_filho < 8:
                    for filho in estrutura.get(cod, []):
                        comp = filho["componente"]
                        qtd_por_un = float(filho["quantidade"])
                        necessidade_bruta[comp][idx_demanda_filho] += (
                            rec_plan[idx] * qtd_por_un
                        )

        registros_mrp[cod] = {
            "codigo": cod,
            "descricao": item["descricao"],
            "tipo": tipo,
            "lead_time": lead_time,
            "estoque_seguranca": est_seg,
            "lote_minimo": lote_min,
            "estoque_inicial": estoque_inicial,
            "necessidade_bruta": nb,
            "recebimentos_programados": rp,
            "estoque_projetado": ep,
            "necessidade_liquida": nl,
            "recebimentos_planejados": rec_plan,
            "liberacoes_planejadas": lib_plan,
        }

    todas_ordens = ordens_mantidas + novas_ordens
    if salvar_ordens:
        salvar_json("ordens", todas_ordens)

    return registros_mrp, todas_ordens, mensagens_excecao


def exibir_registro_item_mrp(registro: dict) -> None:
    print(f"\nREGISTRO MRP - {registro['codigo']} {registro['descricao']}")
    print(
        f"Lead time: {registro['lead_time']} sem | "
        f"Est. seguranca: {registro['estoque_seguranca']:g} | "
        f"Lote min.: {registro['lote_minimo']:g} | "
        f"Estoque: {registro['estoque_inicial']:g}"
    )

    cab_semanas = " ".join([f"{s:>6}" for s in range(1, 9)])
    print(f"{'Semana':<22} {cab_semanas}")
    print("-" * 78)

    linhas = [
        ("Necessidade bruta", registro["necessidade_bruta"]),
        ("Receb. programados", registro["recebimentos_programados"]),
        ("Estoque projetado", registro["estoque_projetado"]),
        ("Necessidade liquida", registro["necessidade_liquida"]),
        ("Receb. planejados", registro["recebimentos_planejados"]),
        ("Liberacao planejada", registro["liberacoes_planejadas"]),
    ]

    for rotulo, valores in linhas:
        vals_fmt = " ".join([f"{v:>6g}" for v in valores])
        print(f"{rotulo:<22} {vals_fmt}")


def executar_e_exibir_mrp() -> None:
    registros, ordens, excecoes = calcular_mrp(salvar_ordens=True)

    planejadas = [o for o in ordens if o["status"] in ("PLANEJADA", "ATRASADA")]
    print(f"\nMRP executado com sucesso em {obter_data_atual()}!")
    print(f"Total de ordens planejadas/atrasadas geradas: {len(planejadas)}")

    if excecoes:
        print(f"\n{len(excecoes)} mensagens de excecao:")
        for msg in excecoes:
            print(f"  - {msg}")

    while True:
        cod = input(
            "\nCódigo do item para ver registro MRP (ou Enter para voltar): "
        ).strip().upper()
        if not cod:
            break
        if cod not in registros:
            print("ERRO: Item não encontrado.")
            continue
        exibir_registro_item_mrp(registros[cod])