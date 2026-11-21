import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from capacidade import calcular_carga_semanal_centro
from custos import atualizar_todos_custos_padrao, calcular_custo_unitario_recursivo
from estoque import registrar_movimentacao
from graficos import (
    grafico_crp_centro,
    grafico_estoque_projetado_mrp,
    grafico_ordens_por_semana,
    grafico_posicao_estoque,
)
from ia_demanda import prever_demanda_ia
from mrp import calcular_mrp
from persistencia import (
    carregar_json,
    carregar_movimentos_csv,
    inicializar_base_demonstracao,
    salvar_json,
)
from relatorios import exportar_todos_relatorios


class SistemaMRP2GUI:

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MRP II — Pedal Forte Bicicletas (GPTech Sistemas)")
        self.root.geometry("1060x660")

        inicializar_base_demonstracao()
        atualizar_todos_custos_padrao()

        self._configurar_estilo()
        self._criar_cabecalho()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self._construir_aba_itens_bom()
        self._construir_aba_estoque()
        self._construir_aba_mps_ia()
        self._construir_aba_mrp_ordens()
        self._construir_aba_crp_graficos()

        self.atualizar_tudo()

    def _configurar_estilo(self) -> None:
        estilo = ttk.Style()
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")
        estilo.configure("Treeview", rowheight=26, font=("Sans", 10))
        estilo.configure("Treeview.Heading", font=("Sans", 10, "bold"))

    def _criar_cabecalho(self) -> None:
        topo = tk.Frame(self.root, bg="#1b365d", pady=10)
        topo.pack(fill=tk.X)

        tk.Label(
            topo,
            text="MRP II — PEDAL FORTE BICICLETAS",
            fg="white",
            bg="#1b365d",
            font=("Sans", 15, "bold"),
        ).pack(side=tk.LEFT, padx=15)

        ttk.Button(
            topo, text="Exportar CSVs (RF14)", command=self._acao_exportar_csv
        ).pack(side=tk.RIGHT, padx=15)

    def _construir_aba_itens_bom(self) -> None:
        aba = ttk.Frame(self.notebook)
        self.notebook.add(aba, text="1. Itens, BOM & Custos")

        cols = ("codigo", "tipo", "descricao", "un", "custo", "lt", "es", "lote")
        self.tree_itens = ttk.Treeview(aba, columns=cols, show="headings", height=11)
        cabecalhos = [
            ("codigo", "Código", 85),
            ("tipo", "Tipo", 55),
            ("descricao", "Descrição", 260),
            ("un", "Un.", 55),
            ("custo", "Custo Padrão (R$)", 130),
            ("lt", "Lead Time", 85),
            ("es", "Est. Seg.", 85),
            ("lote", "Lote Mín.", 85),
        ]
        for col_id, titulo, largura in cabecalhos:
            self.tree_itens.heading(col_id, text=titulo)
            self.tree_itens.column(col_id, width=largura, anchor=tk.CENTER)
        self.tree_itens.column("descricao", anchor=tk.W)
        self.tree_itens.pack(fill=tk.X, padx=10, pady=8)

        barra_botoes = ttk.Frame(aba)
        barra_botoes.pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(
            barra_botoes,
            text="Explodir Estrutura BOM (RF03)",
            command=self._acao_explodir_bom,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            barra_botoes,
            text="Detalhar Custo Padrão (RF13)",
            command=self._acao_custo_padrao,
        ).pack(side=tk.LEFT, padx=4)

        self.txt_bom = tk.Text(aba, height=11, font=("Courier", 10), bg="#f7f9fc")
        self.txt_bom.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _acao_explodir_bom(self) -> None:
        selecionado = self.tree_itens.focus()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um item PA ou SA na tabela.")
            return
        codigo = self.tree_itens.item(selecionado)["values"][0]
        itens = carregar_json("itens")
        estrutura = carregar_json("estrutura")

        if itens[codigo]["tipo"] == "MP":
            messagebox.showinfo("Info [RN03]", "Matéria-prima (MP) não possui estrutura.")
            return

        linhas = [f"{codigo} - {itens[codigo]['descricao']}"]

        def percorrer(cod: str, pref: str = "") -> None:
            filhos = estrutura.get(cod, [])
            for i, f in enumerate(filhos):
                ult = i == len(filhos) - 1
                con = "└── " if ult else "├── "
                c_cod = f["componente"]
                qtd = f["quantidade"]
                linhas.append(
                    f"{pref}{con}{c_cod} {itens[c_cod]['descricao']} ({qtd:g} {itens[c_cod]['unidade']})"
                )
                percorrer(c_cod, pref + ("    " if ult else "│   "))

        percorrer(codigo)
        self.txt_bom.delete("1.0", tk.END)
        self.txt_bom.insert(tk.END, "\n".join(linhas))

    def _acao_custo_padrao(self) -> None:
        selecionado = self.tree_itens.focus()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um item na tabela.")
            return
        codigo = self.tree_itens.item(selecionado)["values"][0]
        itens = carregar_json("itens")
        estrutura = carregar_json("estrutura")
        centros = carregar_json("centros")
        roteiros = carregar_json("roteiros")

        custo = calcular_custo_unitario_recursivo(
            codigo, itens, estrutura, centros, roteiros
        )
        linhas = [
            f"CUSTO PADRÃO: {codigo} - {itens[codigo]['descricao']}",
            "-" * 55,
        ]
        for f in estrutura.get(codigo, []):
            c_cod = f["componente"]
            c_un = calcular_custo_unitario_recursivo(
                c_cod, itens, estrutura, centros, roteiros
            )
            sub = f["quantidade"] * c_un
            linhas.append(
                f"  {c_cod:<8} {itens[c_cod]['descricao']:<25} {f['quantidade']:>4g} x R$ {c_un:>7.2f} = R$ {sub:>7.2f}"
            )
        rot = roteiros.get(codigo)
        if rot and rot["centro"] in centros:
            ct = centros[rot["centro"]]
            mo = rot["tempo_unitario"] * ct["custo_hora"]
            linhas.append(
                f"  Mão de obra ({rot['centro']}): {rot['tempo_unitario']}h x R$ {ct['custo_hora']:.2f} = R$ {mo:.2f}"
            )
        linhas.append("-" * 55)
        linhas.append(f"CUSTO PADRÃO TOTAL: R$ {custo:.2f}")

        self.txt_bom.delete("1.0", tk.END)
        self.txt_bom.insert(tk.END, "\n".join(linhas))

    def _construir_aba_estoque(self) -> None:
        aba = ttk.Frame(self.notebook)
        self.notebook.add(aba, text="2. Estoque & Kardex")

        cols = ("codigo", "descricao", "un", "saldo", "es", "status")
        self.tree_estoque = ttk.Treeview(aba, columns=cols, show="headings", height=11)
        for col_id, titulo, larg in [
            ("codigo", "Código", 90),
            ("descricao", "Descrição", 300),
            ("un", "Un.", 60),
            ("saldo", "Saldo Atual", 110),
            ("es", "Est. Segurança", 120),
            ("status", "Situação", 140),
        ]:
            self.tree_estoque.heading(col_id, text=titulo)
            self.tree_estoque.column(col_id, width=larg, anchor=tk.CENTER)
        self.tree_estoque.column("descricao", anchor=tk.W)
        self.tree_estoque.tag_configure("alerta", background="#ffd6d6", foreground="#900")
        self.tree_estoque.pack(fill=tk.X, padx=10, pady=8)

        painel_mov = ttk.LabelFrame(aba, text="Movimentação de Estoque (RF04 / RN02)")
        painel_mov.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(painel_mov, text="Item:").pack(side=tk.LEFT, padx=5, pady=8)
        self.cmb_item_est = ttk.Combobox(painel_mov, width=12, state="readonly")
        self.cmb_item_est.pack(side=tk.LEFT, padx=4)

        ttk.Label(painel_mov, text="Tipo:").pack(side=tk.LEFT, padx=5)
        self.cmb_tipo_mov = ttk.Combobox(
            painel_mov, values=["ENTRADA", "SAIDA", "AJUSTE"], width=10, state="readonly"
        )
        self.cmb_tipo_mov.current(0)
        self.cmb_tipo_mov.pack(side=tk.LEFT, padx=4)

        ttk.Label(painel_mov, text="Qtde:").pack(side=tk.LEFT, padx=5)
        self.ent_qtd_mov = ttk.Entry(painel_mov, width=10)
        self.ent_qtd_mov.pack(side=tk.LEFT, padx=4)

        ttk.Label(painel_mov, text="Documento:").pack(side=tk.LEFT, padx=5)
        self.ent_doc_mov = ttk.Entry(painel_mov, width=22)
        self.ent_doc_mov.pack(side=tk.LEFT, padx=4)

        ttk.Button(
            painel_mov, text="Registrar", command=self._acao_movimentar_estoque
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            painel_mov, text="Ver Kardex (RF05)", command=self._acao_ver_kardex
        ).pack(side=tk.LEFT, padx=4)

        self.txt_kardex = tk.Text(aba, height=8, font=("Courier", 10), bg="#f7f9fc")
        self.txt_kardex.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _acao_movimentar_estoque(self) -> None:
        cod = self.cmb_item_est.get()
        tipo = self.cmb_tipo_mov.get()
        doc = self.ent_doc_mov.get().strip() or "Movimento GUI"
        try:
            qtd = float(self.ent_qtd_mov.get().replace(",", "."))
        except ValueError:
            messagebox.showerror("Erro", "Informe uma quantidade numérica válida.")
            return

        ok, msg = registrar_movimentacao(cod, tipo, qtd, doc)
        if ok:
            messagebox.showinfo("Sucesso", msg)
            self.ent_qtd_mov.delete(0, tk.END)
            self.atualizar_tudo()
            self._acao_ver_kardex(cod)
        else:
            messagebox.showerror("Operação Rejeitada", msg)

    def _acao_ver_kardex(self, codigo: str | None = None) -> None:
        cod = codigo or self.cmb_item_est.get()
        if not cod:
            return
        movs = [m for m in carregar_movimentos_csv() if m["codigo"] == cod]
        linhas = [f"KARDEX DO ITEM {cod}", "-" * 65]
        for m in movs:
            linhas.append(
                f"{m['data']:<12} {m['tipo']:<9} {float(m['quantidade']):>+8g} -> Saldo: {float(m['saldo_apos']):>7g} | {m['documento']}"
            )
        self.txt_kardex.delete("1.0", tk.END)
        self.txt_kardex.insert(tk.END, "\n".join(linhas))

    def _construir_aba_mps_ia(self) -> None:
        aba = ttk.Frame(self.notebook)
        self.notebook.add(aba, text="3. MPS & Previsão IA")

        cols = ("codigo", "descricao", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "total")
        self.tree_mps = ttk.Treeview(aba, columns=cols, show="headings", height=6)
        self.tree_mps.heading("codigo", text="Produto")
        self.tree_mps.column("codigo", width=85, anchor=tk.CENTER)
        self.tree_mps.heading("descricao", text="Descrição")
        self.tree_mps.column("descricao", width=230, anchor=tk.W)
        for s in range(1, 9):
            self.tree_mps.heading(f"s{s}", text=f"S{s}")
            self.tree_mps.column(f"s{s}", width=65, anchor=tk.CENTER)
        self.tree_mps.heading("total", text="Total")
        self.tree_mps.column("total", width=80, anchor=tk.CENTER)
        self.tree_mps.pack(fill=tk.X, padx=10, pady=8)

        barra = ttk.Frame(aba)
        barra.pack(fill=tk.X, padx=10, pady=6)
        ttk.Button(
            barra,
            text="Editar Demanda Semana (RF07)",
            command=self._acao_editar_mps,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            barra,
            text="[IA] Prever Demanda 8 Semanas & Aplicar no MPS (Bônus)",
            command=self._acao_prever_ia,
        ).pack(side=tk.LEFT, padx=5)

        self.txt_ia = tk.Text(aba, height=13, font=("Courier", 10), bg="#f7f9fc")
        self.txt_ia.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _acao_editar_mps(self) -> None:
        sel = self.tree_mps.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um Produto Acabado na tabela MPS.")
            return
        cod = self.tree_mps.item(sel)["values"][0]
        sem = simpledialog.askinteger("Semana", "Informe a semana (1 a 8):", minvalue=1, maxvalue=8)
        if not sem:
            return
        qtd = simpledialog.askfloat("Demanda", f"Nova demanda para {cod} na Semana {sem}:", minvalue=0)
        if qtd is None:
            return
        mps = carregar_json("mps")
        lista = (list(mps.get(cod, [0.0] * 8)) + [0.0] * 8)[:8]
        lista[sem - 1] = qtd
        mps[cod] = lista
        salvar_json("mps", mps)
        self.atualizar_tudo()

    def _acao_prever_ia(self) -> None:
        sel = self.tree_mps.focus()
        cod = self.tree_mps.item(sel)["values"][0] if sel else "PA-001"
        res = prever_demanda_ia(cod, horizonte=8)

        mps = carregar_json("mps")
        mps[cod] = res["previsao"]
        salvar_json("mps", mps)
        self.atualizar_tudo()

        texto = (
            f"=== PREVISÃO DE DEMANDA POR IA (REGRESSÃO LINEAR + SAZONALIDADE) ===\n"
            f"Produto analisado: {cod}\n"
            f"Equação de Tendência: Y(t) = {res['intercepto']} + ({res['inclinacao']}) * t\n"
            f"Índices Sazonais (ciclo 4 sem): {res['indices_sazonais']}\n"
            f"Erro Médio Percentual (MAPE): {res['mape']}%\n"
            f"Histórico Base (12 semanas): {[int(x) for x in res['historico']]}\n"
            f"Previsão Aplicada ao MPS (S1..S8): {[int(x) for x in res['previsao']]}\n"
        )
        self.txt_ia.delete("1.0", tk.END)
        self.txt_ia.insert(tk.END, texto)
        messagebox.showinfo("IA Concluída", f"MPS de {cod} atualizado pela IA (MAPE: {res['mape']}%)!")

    def _construir_aba_mrp_ordens(self) -> None:
        aba = ttk.Frame(self.notebook)
        self.notebook.add(aba, text="4. Cálculo MRP & Ordens")

        barra_topo = ttk.Frame(aba)
        barra_topo.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(
            barra_topo, text="▶ EXECUTAR MRP (RF08 / RF09)", command=self._acao_rodar_mrp
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            barra_topo, text="Firmar Ordem (RF10)", command=lambda: self._mudar_status_ordem("FIRME")
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            barra_topo, text="Liberar Ordem (RF10)", command=lambda: self._mudar_status_ordem("LIBERADA")
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(
            barra_topo, text="Apontar / Encerrar (RF11)", command=self._acao_apontar_ordem
        ).pack(side=tk.LEFT, padx=4)

        cols = ("numero", "tipo", "item", "qtde", "liberar", "entregar", "status")
        self.tree_ordens = ttk.Treeview(aba, columns=cols, show="headings", height=13)
        for cid, tit, larg in [
            ("numero", "Ordem", 100),
            ("tipo", "Tipo", 70),
            ("item", "Item", 100),
            ("qtde", "Quantidade", 110),
            ("liberar", "Liberar", 90),
            ("entregar", "Entregar", 90),
            ("status", "Status", 140),
        ]:
            self.tree_ordens.heading(cid, text=tit)
            self.tree_ordens.column(cid, width=larg, anchor=tk.CENTER)
        self.tree_ordens.tag_configure("ATRASADA", background="#ffd6d6", foreground="#900")
        self.tree_ordens.tag_configure("ENCERRADA", background="#dff0d8", foreground="#2b542c")
        self.tree_ordens.pack(fill=tk.X, padx=10, pady=4)

        self.txt_excecoes = tk.Text(aba, height=7, font=("Courier", 10), bg="#fff9f0")
        self.txt_excecoes.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _acao_rodar_mrp(self) -> None:
        _, ordens, excecoes = calcular_mrp(salvar_ordens=True)
        self.atualizar_tudo()
        self.txt_excecoes.delete("1.0", tk.END)
        if excecoes:
            self.txt_excecoes.insert(tk.END, "\n".join(excecoes))
        else:
            self.txt_excecoes.insert(tk.END, "MRP executado sem mensagens de exceção.")
        messagebox.showinfo("MRP", f"Cálculo concluído! Total de ordens na carteira: {len(ordens)}.")

    def _mudar_status_ordem(self, novo_status: str) -> None:
        sel = self.tree_ordens.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma ordem na tabela.")
            return
        num = self.tree_ordens.item(sel)["values"][0]
        ordens = carregar_json("ordens", padrao=[])
        for o in ordens:
            if o["numero"] == num:
                if novo_status == "FIRME" and o["status"] not in ("PLANEJADA", "ATRASADA"):
                    messagebox.showerror("Erro", "Apenas ordens PLANEJADA/ATRASADA podem ser firmadas.")
                    return
                if novo_status == "LIBERADA" and o["status"] != "FIRME":
                    messagebox.showerror("Erro", "A ordem precisa estar FIRME antes de ser liberada.")
                    return
                o["status"] = novo_status
                salvar_json("ordens", ordens)
                self.atualizar_tudo()
                return

    def _acao_apontar_ordem(self) -> None:
        sel = self.tree_ordens.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma ordem LIBERADA na tabela.")
            return
        num = self.tree_ordens.item(sel)["values"][0]
        ordens = carregar_json("ordens", padrao=[])
        itens = carregar_json("itens")
        estrutura = carregar_json("estrutura")
        estoque = carregar_json("estoque")

        for o in ordens:
            if o["numero"] == num:
                if o["status"] != "LIBERADA":
                    messagebox.showerror("Erro [RF11]", "A ordem precisa estar LIBERADA para apontamento.")
                    return
                if o["tipo"] == "OC":
                    registrar_movimentacao(o["item"], "ENTRADA", float(o["quantidade"]), f"Recebimento {num}")
                    o["status"] = "ENCERRADA"
                    salvar_json("ordens", ordens)
                    self.atualizar_tudo()
                    messagebox.showinfo("Sucesso", f"OC {num} encerrada e estoque atualizado!")
                    return

                comps = estrutura.get(o["item"], [])
                for c in comps:
                    nec = float(o["quantidade"]) * float(c["quantidade"])
                    disp = float(estoque.get(c["componente"], 0.0))
                    if disp < nec:
                        messagebox.showerror(
                            "Falta de Componente [RF11]",
                            f"Saldo insuficiente de {c['componente']} ({itens[c['componente']]['descricao']}): "
                            f"necessário {nec:g}, disponível {disp:g}.",
                        )
                        return

                for c in comps:
                    nec = float(o["quantidade"]) * float(c["quantidade"])
                    registrar_movimentacao(c["componente"], "SAIDA", nec, f"{num} ({o['item']})")
                registrar_movimentacao(o["item"], "ENTRADA", float(o["quantidade"]), num)
                o["status"] = "ENCERRADA"
                salvar_json("ordens", ordens)
                self.atualizar_tudo()
                messagebox.showinfo("Sucesso", f"Produção da {num} apontada e encerrada!")
                return

    def _construir_aba_crp_graficos(self) -> None:
        aba = ttk.Frame(self.notebook)
        self.notebook.add(aba, text="5. CRP & Gráficos (RF16)")

        topo_crp = ttk.Frame(aba)
        topo_crp.pack(fill=tk.X, padx=10, pady=8)
        ttk.Label(topo_crp, text="Centro de Trabalho:").pack(side=tk.LEFT, padx=5)
        self.cmb_centro = ttk.Combobox(topo_crp, values=["CT-01", "CT-02", "CT-03"], width=10, state="readonly")
        self.cmb_centro.current(2)
        self.cmb_centro.pack(side=tk.LEFT, padx=5)
        ttk.Button(topo_crp, text="Calcular CRP (RF12)", command=self._acao_calcular_crp).pack(side=tk.LEFT, padx=5)

        self.txt_crp = tk.Text(aba, height=13, font=("Courier", 10), bg="#f7f9fc")
        self.txt_crp.pack(fill=tk.X, padx=10, pady=6)

        painel_graf = ttk.LabelFrame(aba, text="Gerar Gráficos Matplotlib e Salvar PNG em docs/ (RF16)")
        painel_graf.pack(fill=tk.X, padx=10, pady=8)

        ttk.Button(
            painel_graf, text="1. Posição de Estoque", command=grafico_posicao_estoque
        ).pack(side=tk.LEFT, padx=6, pady=8)
        ttk.Button(
            painel_graf,
            text="2. Estoque Projetado MRP (SA-020)",
            command=lambda: grafico_estoque_projetado_mrp(self.cmb_item_est.get() or "SA-020"),
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            painel_graf, text="3. Ordens OP x OC por Semana", command=grafico_ordens_por_semana
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            painel_graf,
            text="4. Carga x Capacidade (CRP)",
            command=lambda: grafico_crp_centro(self.cmb_centro.get()),
        ).pack(side=tk.LEFT, padx=6)

    def _acao_calcular_crp(self) -> None:
        cod = self.cmb_centro.get()
        centros = carregar_json("centros")
        ct = centros[cod]
        cap = float(ct["capacidade_semanal"])
        carga = calcular_carga_semanal_centro(cod)

        linhas = [
            f"CARGA x CAPACIDADE - {cod} {ct['descricao']} ({cap:.1f} h/semana)",
            f"{'Sem':<5} {'Carga(h)':>9} {'Uso(%)':>8}  Situação",
            "-" * 55,
        ]
        for s in range(1, 9):
            c = carga[s]
            pct = (c / cap * 100.0) if cap > 0 else 0.0
            status = "SOBRECARGA!" if c > cap else "OK"
            linhas.append(f"S{s:<4} {c:>9.1f} {pct:>7.0f}%  {status}")

        self.txt_crp.delete("1.0", tk.END)
        self.txt_crp.insert(tk.END, "\n".join(linhas))

    def _acao_exportar_csv(self) -> None:
        exportar_todos_relatorios()
        messagebox.showinfo("Relatórios CSV", "Arquivos salvos em docs/posicao_estoque.csv e docs/lista_ordens.csv!")

    def atualizar_tudo(self) -> None:
        """Recarrega todas as tabelas da interface a partir dos arquivos JSON."""
        itens = carregar_json("itens")
        estoque = carregar_json("estoque")
        mps = carregar_json("mps")
        ordens = carregar_json("ordens", padrao=[])

        # Tabela Itens
        self.tree_itens.delete(*self.tree_itens.get_children())
        for cod in sorted(itens.keys()):
            d = itens[cod]
            self.tree_itens.insert(
                "",
                tk.END,
                values=(
                    cod,
                    d["tipo"],
                    d["descricao"],
                    d["unidade"],
                    f"{d['custo_unitario']:.2f}",
                    f"{d['lead_time']} sem",
                    f"{d['estoque_seguranca']:g}",
                    f"{d['lote_minimo']:g}",
                ),
            )

        self.tree_estoque.delete(*self.tree_estoque.get_children())
        codigos_lista = sorted(itens.keys())
        self.cmb_item_est["values"] = codigos_lista
        if codigos_lista and not self.cmb_item_est.get():
            self.cmb_item_est.current(0)

        for cod in codigos_lista:
            d = itens[cod]
            saldo = float(estoque.get(cod, 0.0))
            es = float(d["estoque_seguranca"])
            tag = ("alerta",) if saldo < es else ()
            self.tree_estoque.insert(
                "",
                tk.END,
                values=(cod, d["descricao"], d["unidade"], f"{saldo:g}", f"{es:g}", "ABAIXO ES!" if saldo < es else "OK"),
                tags=tag,
            )

        self.tree_mps.delete(*self.tree_mps.get_children())
        for cod in codigos_lista:
            if itens[cod]["tipo"] == "PA":
                dem = (list(mps.get(cod, [0.0] * 8)) + [0.0] * 8)[:8]
                vals = [cod, itens[cod]["descricao"]] + [f"{v:g}" for v in dem] + [f"{sum(dem):g}"]
                self.tree_mps.insert("", tk.END, values=vals)

        self.tree_ordens.delete(*self.tree_ordens.get_children())
        for o in ordens:
            st = o["status"]
            tag = (st,) if st in ("ATRASADA", "ENCERRADA") else ()
            self.tree_ordens.insert(
                "",
                tk.END,
                values=(
                    o["numero"],
                    o["tipo"],
                    o["item"],
                    f"{o['quantidade']:g}",
                    f"S{o['semana_liberacao']}",
                    f"S{o['semana_entrega']}",
                    st,
                ),
                tags=tag,
            )


def iniciar_gui() -> None:
    root = tk.Tk()
    SistemaMRP2GUI(root)
    root.mainloop()


if __name__ == "__main__":
    iniciar_gui()