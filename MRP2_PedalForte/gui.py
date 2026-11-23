"""Interface grafica em Tkinter (bonus - RNF11).

Inicie com::

    python main.py --gui

A interface reutiliza exatamente as mesmas funcoes de negocio do modo texto
(itens, estoque, mrp, ordens...), portanto as regras RN01 a RN10 valem
igualmente aqui. A preparacao dos dados exibidos nas tabelas fica em
``visoes.py`` (testavel sem janela); este modulo so monta os widgets.

Organizacao: uma classe ``Aplicacao`` (janela, tratamento de erros e
gravacao) e uma classe por aba (``AbaItens``, ``AbaEstoque``...), cada uma
com um metodo ``atualizar`` chamado apos toda operacao bem-sucedida.
"""

import tkinter as tk
from functools import partial
from tkinter import messagebox, ttk

import custos
import estoque
import estrutura
import graficos
import itens
import mps
import mrp
import ordens
import persistencia
import previsao
import relatorios
import visoes
from utils import (
    HORIZONTE,
    ErroNegocio,
    converter_data,
    converter_inteiro,
    converter_numero,
    formatar_data,
    formatar_numero,
    hoje_iso,
)

TITULO = "MRP II - Pedal Forte Bicicletas"
FONTE_TITULO = ("Helvetica", 16, "bold")
CORES_LINHAS = {
    "alerta": "#fadbd8",
    "atrasada": "#fadbd8",
    "firme": "#fcf3cf",
    "liberada": "#d6eaf8",
    "encerrada": "#e5e8e8",
    "escolhido": "#d5f5e3",
}
SEMANAS_COLUNAS = [(f"s{s}", f"S{s}", 55, "e")
                   for s in range(1, HORIZONTE + 1)]


def criar_tabela(pai, colunas, altura=10, titulo_arvore=None):
    """Cria uma Treeview com barra de rolagem.

    `colunas` e uma lista de ``(id, titulo, largura, alinhamento)``. Se
    `titulo_arvore` for informado, a tabela mostra tambem a coluna de
    arvore (#0), usada para a BOM. Devolve ``(quadro, tabela)``.
    """
    quadro = ttk.Frame(pai)
    mostrar = "tree headings" if titulo_arvore else "headings"
    tabela = ttk.Treeview(quadro, columns=[c[0] for c in colunas],
                          show=mostrar, height=altura, selectmode="browse")
    if titulo_arvore:
        tabela.heading("#0", text=titulo_arvore)
        tabela.column("#0", width=140, anchor="w")
    for ident, titulo, largura, alinhamento in colunas:
        tabela.heading(ident, text=titulo)
        tabela.column(ident, width=largura, anchor=alinhamento)
    barra = ttk.Scrollbar(quadro, orient="vertical", command=tabela.yview)
    tabela.configure(yscrollcommand=barra.set)
    tabela.grid(row=0, column=0, sticky="nsew")
    barra.grid(row=0, column=1, sticky="ns")
    quadro.rowconfigure(0, weight=1)
    quadro.columnconfigure(0, weight=1)
    for tag, cor in CORES_LINHAS.items():
        tabela.tag_configure(tag, background=cor)
    return quadro, tabela


def preencher(tabela, linhas):
    """Substitui o conteudo da tabela por `linhas` ((valores, tag))."""
    tabela.delete(*tabela.get_children())
    for valores, tag in linhas:
        tabela.insert("", "end", values=valores,
                      tags=(tag,) if tag else ())


def valor_selecionado(tabela, coluna=0):
    """Valor (texto) da coluna indicada na linha selecionada, ou None."""
    selecao = tabela.selection()
    if not selecao:
        return None
    return str(tabela.item(selecao[0], "values")[coluna])


def definir_opcoes(combo, variavel, opcoes):
    """Atualiza as opcoes de uma Combobox preservando a escolha atual."""
    combo.configure(values=opcoes)
    if variavel.get() not in opcoes:
        variavel.set(opcoes[0] if opcoes else "")


def botao(pai, texto, comando, **opcoes):
    """Botao ttk ja posicionado a esquerda."""
    widget = ttk.Button(pai, text=texto, command=comando)
    widget.pack(side="left", padx=(0, 6), **opcoes)
    return widget


class QuadroGrafico:
    """Area que exibe uma Figure do matplotlib dentro da janela."""

    def __init__(self, pai, largura=6.5, altura=3.6):
        self.quadro = ttk.Frame(pai)
        self.largura = largura
        self.altura = altura
        self.canvas = None
        self.figura = None
        self.aviso = ttk.Label(self.quadro, anchor="center",
                               text="Nenhum grafico gerado ainda.")
        self.aviso.pack(fill="both", expand=True)

    def limpar(self, texto="Nenhum grafico gerado ainda."):
        """Remove o grafico atual e mostra uma mensagem."""
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None
        self.figura = None
        self.aviso.configure(text=texto)
        self.aviso.pack(fill="both", expand=True)

    def mostrar(self, desenhar):
        """Cria uma Figure, chama ``desenhar(figura)`` e a exibe."""
        try:
            graficos.exigir_matplotlib()
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure
            figura = Figure(figsize=(self.largura, self.altura), dpi=100)
            desenhar(figura)
            figura.tight_layout()
        except ErroNegocio as erro:
            self.limpar(str(erro))
            return False
        except ImportError as erro:
            self.limpar(f"Nao foi possivel carregar o matplotlib: {erro}")
            return False
        self.limpar()
        self.aviso.pack_forget()
        self.figura = figura
        self.canvas = FigureCanvasTkAgg(figura, master=self.quadro)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        return True

    def salvar_png(self, nome_arquivo):
        """Salva o grafico exibido em saida/ e devolve o caminho."""
        if self.figura is None:
            raise ErroNegocio("gere um grafico antes de salva-lo.")
        persistencia.PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
        caminho = persistencia.PASTA_SAIDA / nome_arquivo
        self.figura.savefig(caminho, dpi=120)
        return caminho


class Formulario:
    """Janela modal com varios campos.

    Cada campo e um dicionario com ``nome`` e ``rotulo`` e, opcionalmente,
    ``padrao``, ``opcoes`` (vira lista de escolha) e ``somente_leitura``.
    Ao confirmar, ``ao_confirmar(valores)`` recebe um dicionario com os
    textos digitados e devolve True para fechar a janela ou False para
    mante-la aberta (por exemplo, quando ha erro de validacao).
    """

    def __init__(self, aplicacao, titulo, campos, ao_confirmar,
                 texto_botao="Confirmar"):
        self.ao_confirmar = ao_confirmar
        self.variaveis = {}
        self.janela = tk.Toplevel(aplicacao.raiz)
        self.janela.title(titulo)
        self.janela.transient(aplicacao.raiz)
        self.janela.resizable(False, False)
        quadro = ttk.Frame(self.janela, padding=12)
        quadro.grid(row=0, column=0)
        primeiro = None
        for linha, campo in enumerate(campos):
            ttk.Label(quadro, text=campo["rotulo"]).grid(
                row=linha, column=0, sticky="w", padx=(0, 10), pady=3)
            variavel = tk.StringVar(value=str(campo.get("padrao", "")))
            if "opcoes" in campo:
                widget = ttk.Combobox(quadro, textvariable=variavel,
                                      values=campo["opcoes"],
                                      state="readonly", width=38)
            else:
                widget = ttk.Entry(quadro, textvariable=variavel, width=40)
                if campo.get("somente_leitura"):
                    widget.configure(state="readonly")
            widget.grid(row=linha, column=1, sticky="ew", pady=3)
            self.variaveis[campo["nome"]] = variavel
            if primeiro is None:
                primeiro = widget
        botoes = ttk.Frame(quadro)
        botoes.grid(row=len(campos), column=0, columnspan=2, sticky="e",
                    pady=(12, 0))
        ttk.Button(botoes, text="Cancelar",
                   command=self.janela.destroy).pack(side="right",
                                                     padx=(6, 0))
        ttk.Button(botoes, text=texto_botao,
                   command=self.confirmar).pack(side="right")
        self.janela.bind("<Return>", lambda _evento: self.confirmar())
        self.janela.bind("<Escape>", lambda _evento: self.janela.destroy())
        self.janela.geometry(f"+{aplicacao.raiz.winfo_rootx() + 90}"
                             f"+{aplicacao.raiz.winfo_rooty() + 90}")
        if primeiro is not None:
            primeiro.focus_set()
        try:
            self.janela.wait_visibility()
            self.janela.grab_set()
        except tk.TclError:
            pass  # alguns gerenciadores de janela nao permitem o grab

    def confirmar(self):
        """Le os campos e chama a acao; fecha a janela se deu certo."""
        valores = {nome: variavel.get().strip()
                   for nome, variavel in self.variaveis.items()}
        if self.ao_confirmar(valores):
            self.janela.destroy()


class Aplicacao:
    """Janela principal: abas, tratamento de erros e gravacao dos dados."""

    def __init__(self, dados, raiz=None):
        self.dados = dados
        self.raiz = raiz if raiz is not None else tk.Tk()
        self.raiz.title(TITULO)
        self.raiz.geometry("1280x780")
        self.raiz.minsize(1050, 640)
        self.status = tk.StringVar(value="Pronto.")
        self.abas = []
        self._configurar_estilo()
        self._montar_menu()
        ttk.Label(self.raiz, textvariable=self.status, relief="sunken",
                  anchor="w", padding=(8, 2)).pack(side="bottom", fill="x")
        self.notebook = ttk.Notebook(self.raiz)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        for classe in (AbaPainel, AbaItens, AbaEstrutura, AbaEstoque,
                       AbaMPS, AbaPrevisao, AbaMRP, AbaOrdens, AbaCRP,
                       AbaCustos, AbaRelatorios):
            aba = classe(self, self.notebook)
            self.notebook.add(aba.quadro, text=classe.titulo)
            self.abas.append(aba)
        self.atualizar_tudo()
        self.raiz.protocol("WM_DELETE_WINDOW", self.fechar)

    # -- configuracao --------------------------------------------------------
    def _configurar_estilo(self):
        estilo = ttk.Style(self.raiz)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Treeview", rowheight=24)
        estilo.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))

    def _montar_menu(self):
        barra = tk.Menu(self.raiz)
        arquivo = tk.Menu(barra, tearoff=0)
        arquivo.add_command(label="Gravar dados agora", command=self.gravar)
        arquivo.add_command(label="Restaurar base de demonstracao",
                            command=self.restaurar_demo)
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self.fechar)
        barra.add_cascade(label="Arquivo", menu=arquivo)
        ajuda = tk.Menu(barra, tearoff=0)
        ajuda.add_command(label="Sobre", command=self.sobre)
        barra.add_cascade(label="Ajuda", menu=ajuda)
        self.raiz.configure(menu=barra)

    # -- mensagens -----------------------------------------------------------
    def erro(self, texto):
        """Mostra uma mensagem de erro."""
        self.status.set("Operacao nao realizada.")
        messagebox.showerror("Operacao nao realizada", texto,
                             parent=self.raiz)

    def aviso(self, texto, titulo="Atencao"):
        """Mostra uma mensagem informativa."""
        messagebox.showinfo(titulo, texto, parent=self.raiz)

    def confirmar(self, pergunta, titulo="Confirmacao"):
        """Pergunta sim/nao ao usuario."""
        return bool(messagebox.askyesno(titulo, pergunta, parent=self.raiz))

    def sobre(self):
        """Janela 'Sobre'."""
        self.aviso("MRP II - Pedal Forte Bicicletas\n"
                   "Trabalho 2 - Programacao em Python (CEFET-MG Divinopolis)"
                   "\n\nMesmas regras de negocio do modo texto, com interface "
                   "grafica Tkinter e previsao de demanda (IA).",
                   titulo="Sobre")

    # -- execucao de operacoes ----------------------------------------------
    def consultar(self, funcao):
        """Executa uma consulta (nao altera dados). Devolve (ok, resultado)."""
        try:
            return True, funcao()
        except ErroNegocio as erro:
            self.erro(str(erro))
        except Exception as erro:  # ultima barreira: a janela nao fecha
            self.erro(f"Erro inesperado ({type(erro).__name__}): {erro}")
        return False, None

    def tentar(self, funcao, mensagem=None):
        """Executa uma operacao que altera dados.

        Em caso de sucesso grava os arquivos, atualiza todas as abas e
        mostra `mensagem` na barra de status. Devolve (ok, resultado).
        """
        ok, resultado = self.consultar(funcao)
        if not ok:
            return False, None
        self.gravar(silencioso=True)
        self.atualizar_tudo()
        if mensagem:
            self.status.set(mensagem)
        return True, resultado

    def gravar(self, silencioso=False):
        """Grava todos os dados em data/ (RF15)."""
        try:
            persistencia.salvar_tudo(self.dados)
        except persistencia.ErroPersistencia as erro:
            self.erro(f"Erro ao gravar os dados: {erro}")
            return
        if not silencioso:
            self.status.set("Dados gravados em data/.")

    def atualizar_tudo(self):
        """Atualiza o conteudo de todas as abas."""
        for aba in self.abas:
            aba.atualizar()

    def restaurar_demo(self):
        """Substitui todos os dados pela base de demonstracao."""
        if not self.confirmar("Isto substitui TODOS os dados atuais pela "
                              "base de demonstracao. Continuar?"):
            return
        novos = persistencia.gerar_base_demo()
        self.dados.clear()
        self.dados.update(novos)
        self.gravar(silencioso=True)
        self.atualizar_tudo()
        self.status.set("Base de demonstracao restaurada.")

    def fechar(self):
        """Grava e encerra a aplicacao."""
        self.gravar(silencioso=True)
        self.raiz.destroy()

    def executar(self):
        """Inicia o laco de eventos do Tkinter."""
        self.raiz.mainloop()


class AbaPainel:
    """Indicadores gerais e alertas."""

    titulo = "Painel"
    CARTOES = (
        ("itens", "Itens cadastrados"),
        ("abaixo", "Abaixo do estoque de seguranca"),
        ("abertas", "Ordens abertas"),
        ("atrasadas", "Ordens atrasadas"),
        ("sobrecarga", "Centros em sobrecarga"),
        ("valor", "Valor em estoque (R$)"),
        ("mrp", "Ultimo MRP"),
    )

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        self.indicadores = {}
        cartoes = ttk.Frame(self.quadro)
        cartoes.pack(fill="x")
        for coluna, (chave, rotulo) in enumerate(self.CARTOES):
            cartao = ttk.LabelFrame(cartoes, text=rotulo, padding=8)
            cartao.grid(row=0, column=coluna, padx=4, sticky="nsew")
            cartoes.columnconfigure(coluna, weight=1)
            variavel = tk.StringVar(value="-")
            ttk.Label(cartao, textvariable=variavel,
                      font=FONTE_TITULO).pack()
            self.indicadores[chave] = variavel

        acoes = ttk.Frame(self.quadro)
        acoes.pack(fill="x", pady=8)
        botao(acoes, "Executar MRP agora", self.executar_mrp)
        botao(acoes, "Atualizar painel", self.atualizar)

        meio = ttk.Frame(self.quadro)
        meio.pack(fill="both", expand=True)
        meio.columnconfigure(0, weight=1)
        meio.columnconfigure(1, weight=1)
        meio.rowconfigure(0, weight=1)
        esquerda = ttk.LabelFrame(meio, text="Itens abaixo do estoque de "
                                  "seguranca", padding=6)
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        quadro, self.tabela_alertas = criar_tabela(esquerda, [
            ("codigo", "Codigo", 80, "w"), ("descricao", "Descricao", 220,
                                            "w"),
            ("saldo", "Saldo", 70, "e"), ("es", "Est. seg.", 70, "e")])
        quadro.pack(fill="both", expand=True)
        direita = ttk.LabelFrame(meio, text="Excecoes do ultimo MRP "
                                 "(ordens atrasadas)", padding=6)
        direita.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        quadro, self.tabela_excecoes = criar_tabela(
            direita, [("mensagem", "Mensagem", 560, "w")])
        quadro.pack(fill="both", expand=True)

    def executar_mrp(self):
        """Atalho para executar o MRP."""
        executar_mrp_com_resumo(self.app)

    def atualizar(self):
        """Recalcula os indicadores."""
        resumo = visoes.resumo_painel(self.app.dados)
        sobrecarga = resumo["centros_sobrecarga"]
        textos = {
            "itens": str(resumo["itens"]),
            "abaixo": str(len(resumo["abaixo_seguranca"])),
            "abertas": str(resumo["ordens_abertas"]),
            "atrasadas": str(resumo["ordens_atrasadas"]),
            "sobrecarga": (", ".join(sorted(sobrecarga)) if sobrecarga
                           else "nenhum"),
            "valor": f"{resumo['valor_estoque']:,.2f}",
            "mrp": resumo["mrp_executado_em"],
        }
        for chave, texto in textos.items():
            self.indicadores[chave].set(texto)
        preencher(self.tabela_alertas, [
            ((p["codigo"], p["descricao"], formatar_numero(p["saldo"]),
              formatar_numero(p["estoque_seguranca"])), "alerta")
            for p in resumo["abaixo_seguranca"]])
        preencher(self.tabela_excecoes,
                  [((m,), None) for m in resumo["mensagens"]])


def executar_mrp_com_resumo(app):
    """Executa o MRP e mostra o resumo (usado por mais de uma aba)."""
    ok, resumo = app.tentar(lambda: mrp.executar_mrp(app.dados),
                            "MRP executado.")
    if ok:
        app.aviso(f"MRP executado com sucesso.\n\n"
                  f"{len(resumo['criadas'])} ordens planejadas geradas.\n"
                  f"{len(resumo['mensagens'])} mensagens de excecao "
                  "(ordens com liberacao antes da semana 1).",
                  titulo="MRP")


class AbaItens:
    """Cadastro de itens (RF02)."""

    titulo = "Itens"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        ttk.Label(topo, text="Tipo:").pack(side="left", padx=(0, 4))
        self.filtro = tk.StringVar(value="Todos")
        combo = ttk.Combobox(topo, textvariable=self.filtro, width=8,
                             state="readonly",
                             values=["Todos", "PA", "SA", "MP"])
        combo.pack(side="left", padx=(0, 12))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.atualizar())
        botao(topo, "Novo item", self.novo)
        botao(topo, "Alterar item selecionado", self.alterar)
        quadro, self.tabela = criar_tabela(self.quadro, [
            ("codigo", "Codigo", 90, "w"), ("descricao", "Descricao", 280,
                                            "w"),
            ("tipo", "Tipo", 50, "center"), ("un", "Un", 50, "center"),
            ("custo", "Custo un. (R$)", 110, "e"),
            ("lt", "Lead time (sem)", 110, "e"),
            ("es", "Est. seguranca", 110, "e"),
            ("lote", "Lote minimo", 100, "e")], altura=18)
        quadro.pack(fill="both", expand=True)

    def atualizar(self):
        """Recarrega a lista de itens."""
        tipo = self.filtro.get()
        preencher(self.tabela, visoes.linhas_itens(
            self.app.dados, None if tipo == "Todos" else tipo))

    def novo(self):
        """Abre o formulario de novo item."""
        campos = [
            {"nome": "codigo", "rotulo": "Codigo (ex.: PA-003)"},
            {"nome": "descricao", "rotulo": "Descricao"},
            {"nome": "unidade", "rotulo": "Unidade de medida",
             "padrao": "un"},
            {"nome": "custo", "rotulo": "Custo unitario (R$)",
             "padrao": "0"},
            {"nome": "lead", "rotulo": "Lead time (semanas)", "padrao": "1"},
            {"nome": "seguranca", "rotulo": "Estoque de seguranca",
             "padrao": "0"},
            {"nome": "lote", "rotulo": "Lote minimo", "padrao": "0"},
        ]

        def confirmar(v):
            ok, _ = self.app.tentar(
                lambda: itens.cadastrar_item(
                    self.app.dados, v["codigo"], v["descricao"],
                    v["unidade"], converter_numero(v["custo"]),
                    converter_inteiro(v["lead"]),
                    converter_numero(v["seguranca"]),
                    converter_numero(v["lote"])),
                f"Item {v['codigo'].upper()} cadastrado.")
            return ok

        Formulario(self.app, "Novo item", campos, confirmar)

    def alterar(self):
        """Abre o formulario de alteracao do item selecionado."""
        codigo = valor_selecionado(self.tabela)
        if codigo is None:
            self.app.aviso("Selecione um item na tabela.")
            return
        item = self.app.dados["itens"][codigo]
        campos = [
            {"nome": "codigo", "rotulo": "Codigo", "padrao": codigo,
             "somente_leitura": True},
            {"nome": "descricao", "rotulo": "Descricao",
             "padrao": item["descricao"]},
            {"nome": "unidade", "rotulo": "Unidade de medida",
             "padrao": item["unidade"]},
            {"nome": "custo", "rotulo": "Custo unitario (R$)",
             "padrao": formatar_numero(item["custo_unitario"])},
            {"nome": "lead", "rotulo": "Lead time (semanas)",
             "padrao": item["lead_time"]},
            {"nome": "seguranca", "rotulo": "Estoque de seguranca",
             "padrao": formatar_numero(item["estoque_seguranca"])},
            {"nome": "lote", "rotulo": "Lote minimo",
             "padrao": formatar_numero(item["lote_minimo"])},
        ]

        def confirmar(v):
            ok, _ = self.app.tentar(
                lambda: itens.alterar_item(self.app.dados, codigo, {
                    "descricao": v["descricao"], "unidade": v["unidade"],
                    "custo_unitario": converter_numero(v["custo"]),
                    "lead_time": converter_inteiro(v["lead"]),
                    "estoque_seguranca": converter_numero(v["seguranca"]),
                    "lote_minimo": converter_numero(v["lote"])}),
                f"Item {codigo} alterado.")
            return ok

        Formulario(self.app, f"Alterar item {codigo}", campos, confirmar)


class AbaEstrutura:
    """Estrutura de produto - BOM (RF03)."""

    titulo = "Estrutura (BOM)"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        ttk.Label(topo, text="Item fabricado:").pack(side="left",
                                                     padx=(0, 4))
        self.escolha = tk.StringVar()
        self.combo = ttk.Combobox(topo, textvariable=self.escolha,
                                  width=42, state="readonly")
        self.combo.pack(side="left", padx=(0, 12))
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self.atualizar())
        botao(topo, "Incluir componente", self.incluir)
        botao(topo, "Remover componente selecionado", self.remover)
        self.resumo = tk.StringVar()
        ttk.Label(self.quadro, textvariable=self.resumo).pack(anchor="w",
                                                              pady=(0, 6))
        quadro, self.tabela = criar_tabela(
            self.quadro, [("descricao", "Descricao", 320, "w"),
                          ("qtde", "Qtde por unidade", 120, "e"),
                          ("un", "Un", 60, "center"),
                          ("nivel", "Nivel", 60, "center")],
            altura=18, titulo_arvore="Item")
        quadro.pack(fill="both", expand=True)

    def _codigo(self):
        return visoes.codigo_do_rotulo(self.escolha.get())

    def atualizar(self):
        """Recarrega a arvore da BOM do item escolhido."""
        dados = self.app.dados
        definir_opcoes(self.combo, self.escolha,
                       visoes.rotulos_itens(dados, ("PA", "SA")))
        self.tabela.delete(*self.tabela.get_children())
        if not self.escolha.get():
            self.resumo.set("")
            return
        codigo = self._codigo()
        pais = {}
        for nivel, cod, desc, qtd, un in visoes.linhas_bom(dados, codigo):
            no = self.tabela.insert(pais.get(nivel - 1, ""), "end",
                                    text=cod, open=True,
                                    values=(desc, qtd, un, nivel))
            pais[nivel] = no
        self.resumo.set(visoes.texto_roteiro_e_custo(dados, codigo))

    def incluir(self):
        """Formulario para incluir ou atualizar um componente."""
        pai = self._codigo()
        if not pai:
            return
        campos = [
            {"nome": "pai", "rotulo": "Item pai", "padrao": pai,
             "somente_leitura": True},
            {"nome": "componente", "rotulo": "Componente",
             "opcoes": visoes.rotulos_itens(self.app.dados)},
            {"nome": "quantidade", "rotulo": "Quantidade por unidade do pai",
             "padrao": "1"},
        ]

        def confirmar(v):
            componente = visoes.codigo_do_rotulo(v["componente"])
            ok, _ = self.app.tentar(
                lambda: estrutura.adicionar_componente(
                    self.app.dados, pai, componente,
                    converter_numero(v["quantidade"])),
                f"Componente {componente} incluido em {pai}.")
            return ok

        Formulario(self.app, "Incluir componente na BOM", campos, confirmar)

    def remover(self):
        """Remove o componente selecionado da BOM do seu pai."""
        selecao = self.tabela.selection()
        if not selecao:
            self.app.aviso("Selecione um componente na arvore.")
            return
        no = selecao[0]
        no_pai = self.tabela.parent(no)
        if not no_pai:
            self.app.aviso("Selecione um componente (nao o item raiz).")
            return
        componente = self.tabela.item(no, "text")
        pai = self.tabela.item(no_pai, "text")
        if not self.app.confirmar(f"Remover {componente} da estrutura de "
                                  f"{pai}?"):
            return
        self.app.tentar(
            lambda: estrutura.remover_componente(self.app.dados, pai,
                                                 componente),
            f"Componente {componente} removido de {pai}.")


class AbaEstoque:
    """Estoque: posicao, movimentacao e kardex (RF04, RF05)."""

    titulo = "Estoque"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        botao(topo, "Movimentar estoque", self.movimentar)
        ttk.Label(topo, text="  (selecione um item para ver o kardex)"
                  ).pack(side="left")
        quadro, self.tabela = criar_tabela(self.quadro, [
            ("codigo", "Codigo", 90, "w"), ("descricao", "Descricao", 260,
                                            "w"),
            ("un", "Un", 50, "center"), ("saldo", "Saldo", 90, "e"),
            ("es", "Est. seguranca", 110, "e"),
            ("valor", "Valor (R$)", 110, "e"),
            ("situacao", "Situacao", 120, "w")], altura=9)
        quadro.pack(fill="both", expand=True)
        self.tabela.bind("<<TreeviewSelect>>",
                         lambda _e: self.mostrar_kardex())
        self.alerta = tk.StringVar()
        ttk.Label(self.quadro, textvariable=self.alerta,
                  foreground="#c0392b").pack(anchor="w", pady=(8, 2))
        quadro, self.kardex = criar_tabela(self.quadro, [
            ("data", "Data", 100, "w"), ("tipo", "Tipo", 90, "w"),
            ("qtde", "Qtde", 90, "e"), ("saldo", "Saldo", 90, "e"),
            ("doc", "Documento", 400, "w")], altura=8)
        quadro.pack(fill="both", expand=True)

    def atualizar(self):
        """Recarrega a posicao de estoque e o kardex do item selecionado."""
        selecionado = valor_selecionado(self.tabela)
        preencher(self.tabela, visoes.linhas_posicao(self.app.dados))
        if selecionado:
            for no in self.tabela.get_children():
                if str(self.tabela.item(no, "values")[0]) == selecionado:
                    self.tabela.selection_set(no)
                    break
        self.mostrar_kardex()

    def mostrar_kardex(self):
        """Mostra o kardex do item selecionado na tabela de cima."""
        codigo = valor_selecionado(self.tabela)
        if codigo is None:
            preencher(self.kardex, [])
            self.alerta.set("")
            return
        preencher(self.kardex, visoes.linhas_kardex(self.app.dados, codigo))
        self.alerta.set(estoque.alerta_seguranca(self.app.dados, codigo)
                        or "")

    def movimentar(self):
        """Formulario de movimentacao (entrada, saida ou ajuste)."""
        dados = self.app.dados
        rotulos = visoes.rotulos_itens(dados)
        atual = valor_selecionado(self.tabela)
        padrao = next((r for r in rotulos
                       if visoes.codigo_do_rotulo(r) == atual), "")
        campos = [
            {"nome": "item", "rotulo": "Item", "opcoes": rotulos,
             "padrao": padrao},
            {"nome": "tipo", "rotulo": "Tipo",
             "opcoes": list(estoque.TIPOS_MOVIMENTO), "padrao": "ENTRADA"},
            {"nome": "quantidade",
             "rotulo": "Quantidade (ajuste: negativa reduz)"},
            {"nome": "data", "rotulo": "Data (dd/mm/aaaa)",
             "padrao": formatar_data(hoje_iso())},
            {"nome": "documento", "rotulo": "Documento / motivo"},
        ]

        def confirmar(v):
            codigo = visoes.codigo_do_rotulo(v["item"])
            ok, movimento = self.app.tentar(
                lambda: estoque.registrar_movimento(
                    dados, codigo, v["tipo"],
                    converter_numero(v["quantidade"]), v["documento"],
                    converter_data(v["data"])),
                f"{v['tipo']} registrada em {codigo}.")
            if ok:
                alerta = estoque.alerta_seguranca(dados, codigo)
                if alerta:
                    messagebox.showwarning("Estoque de seguranca", alerta,
                                           parent=self.app.raiz)
            return ok

        Formulario(self.app, "Movimentacao de estoque", campos, confirmar)


class AbaMPS:
    """Plano Mestre de Producao (RF07)."""

    titulo = "MPS"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        botao(topo, "Editar demanda do item selecionado", self.editar)
        ttk.Label(topo, text="  Horizonte de 8 semanas. Para sugerir a "
                  "demanda use a aba Previsao (IA).").pack(side="left")
        colunas = [("codigo", "Codigo", 80, "w"),
                   ("descricao", "Descricao", 230, "w")]
        colunas += [(f"s{s}", f"S{s}", 60, "e")
                    for s in range(1, HORIZONTE + 1)]
        colunas.append(("total", "Total", 80, "e"))
        quadro, self.tabela = criar_tabela(self.quadro, colunas, altura=8)
        quadro.pack(fill="both", expand=True)

    def atualizar(self):
        """Recarrega o MPS."""
        preencher(self.tabela, visoes.linhas_mps(self.app.dados))

    def editar(self):
        """Formulario com a demanda das 8 semanas do PA selecionado."""
        codigo = valor_selecionado(self.tabela)
        if codigo is None:
            self.app.aviso("Selecione um produto acabado na tabela.")
            return
        plano = mps.obter_plano(self.app.dados, codigo)
        campos = [{"nome": "item", "rotulo": "Produto", "padrao": codigo,
                   "somente_leitura": True}]
        campos += [{"nome": f"s{s}", "rotulo": f"Demanda da semana {s}",
                    "padrao": formatar_numero(plano[s - 1])}
                   for s in range(1, HORIZONTE + 1)]

        def confirmar(v):
            ok, _ = self.app.tentar(
                lambda: mps.definir_plano(
                    self.app.dados, codigo,
                    [converter_numero(v[f"s{s}"])
                     for s in range(1, HORIZONTE + 1)]),
                f"MPS de {codigo} atualizado.")
            return ok

        Formulario(self.app, f"Demanda de {codigo}", campos, confirmar)


class AbaPrevisao:
    """Previsao de demanda com aprendizado de series temporais (bonus)."""

    titulo = "Previsao (IA)"

    def __init__(self, app, notebook):
        self.app = app
        self.resultado = None
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        ttk.Label(topo, text="Produto acabado:").pack(side="left",
                                                      padx=(0, 4))
        self.escolha = tk.StringVar()
        self.combo = ttk.Combobox(topo, textvariable=self.escolha,
                                  width=36, state="readonly")
        self.combo.pack(side="left", padx=(0, 12))
        botao(topo, "Calcular previsao", self.calcular)
        botao(topo, "Aplicar ao MPS", self.aplicar)
        botao(topo, "Registrar demanda real", self.registrar)
        self.descricao = tk.StringVar(
            value="Escolha um produto e clique em Calcular previsao.")
        ttk.Label(self.quadro, textvariable=self.descricao).pack(
            anchor="w", pady=(0, 6))
        meio = ttk.Frame(self.quadro)
        meio.pack(fill="both", expand=True)
        meio.columnconfigure(1, weight=1)
        meio.rowconfigure(0, weight=1)
        esquerda = ttk.Frame(meio)
        esquerda.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        ttk.Label(esquerda, text="Desempenho dos modelos (ultimas semanas "
                  "reservadas para teste)").pack(anchor="w")
        quadro, self.tabela_modelos = criar_tabela(esquerda, [
            ("modelo", "Modelo", 190, "w"), ("mae", "MAE", 60, "e"),
            ("rmse", "RMSE", 60, "e"), ("sel", "", 80, "w")], altura=6)
        quadro.pack(fill="x")
        ttk.Label(esquerda, text="Previsao das proximas 8 semanas"
                  ).pack(anchor="w", pady=(10, 0))
        quadro, self.tabela_previsao = criar_tabela(
            esquerda, [("linha", "", 90, "w")] + SEMANAS_COLUNAS, altura=3)
        quadro.pack(fill="x")
        self.grafico = QuadroGrafico(meio)
        self.grafico.quadro.grid(row=0, column=1, sticky="nsew")

    def atualizar(self):
        """Atualiza a lista de produtos acabados."""
        definir_opcoes(self.combo, self.escolha,
                       visoes.rotulos_itens(self.app.dados, ("PA",)))

    def _codigo(self):
        return visoes.codigo_do_rotulo(self.escolha.get())

    def calcular(self):
        """Treina os modelos, escolhe o melhor e mostra a previsao."""
        codigo = self._codigo()
        ok, resultado = self.app.consultar(
            lambda: previsao.prever_demanda_pa(self.app.dados, codigo))
        if not ok:
            return
        self.resultado = resultado
        preencher(self.tabela_modelos, visoes.linhas_modelos(resultado))
        preencher(self.tabela_previsao, visoes.linhas_previsao(resultado))
        self.descricao.set(visoes.descricao_modelo(resultado))
        self.grafico.mostrar(partial(graficos.figura_previsao, resultado))
        self.app.status.set(f"Previsao de {codigo} calculada.")

    def aplicar(self):
        """Grava a previsao calculada como demanda do MPS."""
        if self.resultado is None:
            self.app.aviso("Calcule a previsao antes de aplica-la.")
            return
        codigo = self.resultado["codigo"]
        if not self.app.confirmar(
                f"Substituir a demanda das 8 semanas de {codigo} no MPS "
                "pela previsao?"):
            return
        ok, _ = self.app.tentar(
            lambda: previsao.aplicar_previsao_ao_mps(
                self.app.dados, codigo, self.resultado),
            f"MPS de {codigo} atualizado com a previsao. Execute o MRP.")
        if ok:
            self.app.aviso("MPS atualizado. Va para a aba MRP (ou Painel) e "
                           "execute o MRP para replanejar.", titulo="MPS")

    def registrar(self):
        """Acrescenta a demanda real da ultima semana ao historico."""
        codigo = self._codigo()
        campos = [
            {"nome": "item", "rotulo": "Produto", "padrao": codigo,
             "somente_leitura": True},
            {"nome": "quantidade", "rotulo": "Demanda real da semana"},
        ]

        def confirmar(v):
            ok, _ = self.app.tentar(
                lambda: previsao.adicionar_demanda_real(
                    self.app.dados, codigo, converter_numero(v["quantidade"])),
                f"Demanda real registrada para {codigo}.")
            if ok:
                self.calcular()
            return ok

        Formulario(self.app, "Registrar demanda real", campos, confirmar)


class AbaMRP:
    """Execucao do MRP e registro MRP de um item (RF08, RF09)."""

    titulo = "MRP"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        botao(topo, "Executar MRP", lambda: executar_mrp_com_resumo(app))
        ttk.Label(topo, text="   Registro do item:").pack(side="left")
        self.escolha = tk.StringVar()
        self.combo = ttk.Combobox(topo, textvariable=self.escolha,
                                  width=38, state="readonly")
        self.combo.pack(side="left", padx=6)
        self.combo.bind("<<ComboboxSelected>>",
                        lambda _e: self.mostrar_registro())
        self.descricao = tk.StringVar()
        ttk.Label(self.quadro, textvariable=self.descricao).pack(
            anchor="w", pady=(0, 6))
        colunas = [("indicador", "Semana", 170, "w")] + SEMANAS_COLUNAS
        quadro, self.tabela = criar_tabela(self.quadro, colunas, altura=7)
        quadro.pack(fill="x")
        ttk.Label(self.quadro, text="Mensagens de excecao da ultima "
                  "execucao").pack(anchor="w", pady=(12, 2))
        quadro, self.excecoes = criar_tabela(
            self.quadro, [("mensagem", "Mensagem", 900, "w")], altura=8)
        quadro.pack(fill="both", expand=True)

    def atualizar(self):
        """Atualiza as opcoes e o registro mostrado."""
        definir_opcoes(self.combo, self.escolha,
                       visoes.rotulos_itens(self.app.dados))
        self.mostrar_registro()
        mensagens = self.app.dados["mrp"].get("mensagens", [])
        preencher(self.excecoes, [((m,), "atrasada") for m in mensagens])

    def mostrar_registro(self):
        """Mostra o registro MRP do item escolhido."""
        dados = self.app.dados
        if not mrp.mrp_executado(dados) or not self.escolha.get():
            preencher(self.tabela, [])
            self.descricao.set("O MRP ainda nao foi executado.")
            return
        codigo = visoes.codigo_do_rotulo(self.escolha.get())
        try:
            linhas = visoes.linhas_registro_mrp(dados, codigo)
            texto = visoes.descricao_registro_mrp(dados, codigo)
        except ErroNegocio as erro:
            preencher(self.tabela, [])
            self.descricao.set(str(erro))
            return
        preencher(self.tabela, linhas)
        self.descricao.set(texto)


class AbaOrdens:
    """Ordens de producao e de compra (RF09, RF10, RF11)."""

    titulo = "Ordens"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        botao(topo, "Firmar", self.firmar)
        botao(topo, "Liberar", self.liberar)
        botao(topo, "Apontar producao (OP)", self.apontar)
        botao(topo, "Receber compra (OC)", self.receber)
        botao(topo, "Firmar todas as planejadas", self.firmar_todas)
        self.mostrar_encerradas = tk.BooleanVar(value=False)
        ttk.Checkbutton(topo, text="Mostrar encerradas",
                        variable=self.mostrar_encerradas,
                        command=self.atualizar).pack(side="left", padx=12)
        quadro, self.tabela = criar_tabela(self.quadro, [
            ("numero", "Ordem", 90, "w"), ("tipo", "Tipo", 50, "center"),
            ("item", "Item", 80, "w"), ("descricao", "Descricao", 240, "w"),
            ("qtde", "Qtde", 80, "e"), ("un", "Un", 50, "center"),
            ("lib", "Liberar", 70, "center"),
            ("ent", "Entregar", 70, "center"),
            ("status", "Status", 140, "w")], altura=20)
        quadro.pack(fill="both", expand=True)
        legenda = ("Cores: vermelho = atrasada | amarelo = firme | "
                   "azul = liberada | cinza = encerrada")
        ttk.Label(self.quadro, text=legenda).pack(anchor="w", pady=(6, 0))

    def atualizar(self):
        """Recarrega a lista de ordens."""
        preencher(self.tabela, visoes.linhas_ordens(
            self.app.dados, self.mostrar_encerradas.get()))

    def _numero(self):
        numero = valor_selecionado(self.tabela)
        if numero is None:
            self.app.aviso("Selecione uma ordem na tabela.")
        return numero

    def firmar(self):
        """PLANEJADA -> FIRME."""
        numero = self._numero()
        if numero:
            self.app.tentar(
                lambda: ordens.firmar_ordem(self.app.dados, numero),
                f"Ordem {numero} firmada.")

    def liberar(self):
        """FIRME -> LIBERADA."""
        numero = self._numero()
        if numero:
            self.app.tentar(
                lambda: ordens.liberar_ordem(self.app.dados, numero),
                f"Ordem {numero} liberada.")

    def firmar_todas(self):
        """Firma todas as ordens planejadas."""
        total = len(ordens.listar_ordens(self.app.dados,
                                         status=ordens.PLANEJADA))
        if total == 0:
            self.app.aviso("Nao ha ordens planejadas para firmar.")
            return
        if self.app.confirmar(f"Firmar as {total} ordens planejadas?"):
            self.app.tentar(lambda: ordens.firmar_todas(self.app.dados),
                            f"{total} ordens firmadas.")

    def _pedir_data(self, titulo, funcao, mensagem):
        numero = self._numero()
        if not numero:
            return
        campos = [
            {"nome": "ordem", "rotulo": "Ordem", "padrao": numero,
             "somente_leitura": True},
            {"nome": "data", "rotulo": "Data (dd/mm/aaaa)",
             "padrao": formatar_data(hoje_iso())},
        ]

        def confirmar(v):
            ok, _ = self.app.tentar(
                lambda: funcao(self.app.dados, numero,
                               converter_data(v["data"])),
                mensagem.format(numero=numero))
            return ok

        Formulario(self.app, titulo, campos, confirmar)

    def apontar(self):
        """Apontamento da producao de uma OP liberada (RF11)."""
        self._pedir_data("Apontar producao", ordens.apontar_producao,
                         "Producao de {numero} apontada.")

    def receber(self):
        """Recebimento de uma OC liberada."""
        self._pedir_data("Receber compra", ordens.receber_compra,
                         "Compra {numero} recebida.")


class AbaCRP:
    """Carga x capacidade dos centros de trabalho (RF12)."""

    titulo = "CRP"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        ttk.Label(topo, text="Centro de trabalho:").pack(side="left",
                                                         padx=(0, 4))
        self.escolha = tk.StringVar()
        self.combo = ttk.Combobox(topo, textvariable=self.escolha,
                                  width=40, state="readonly")
        self.combo.pack(side="left")
        self.combo.bind("<<ComboboxSelected>>",
                        lambda _e: self.mostrar_centro())
        meio = ttk.Frame(self.quadro)
        meio.pack(fill="both", expand=True)
        meio.columnconfigure(1, weight=1)
        meio.rowconfigure(0, weight=1)
        esquerda = ttk.Frame(meio)
        esquerda.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        quadro, self.tabela = criar_tabela(esquerda, [
            ("sem", "Semana", 70, "center"), ("carga", "Carga (h)", 80, "e"),
            ("cap", "Capac. (h)", 80, "e"), ("uso", "Uso (%)", 70, "e"),
            ("situacao", "Situacao", 100, "w")], altura=9)
        quadro.pack(fill="x")
        self.sugestao = tk.StringVar()
        ttk.Label(esquerda, textvariable=self.sugestao, wraplength=420,
                  foreground="#c0392b").pack(anchor="w", pady=8)
        self.grafico = QuadroGrafico(meio)
        self.grafico.quadro.grid(row=0, column=1, sticky="nsew")

    def atualizar(self):
        """Atualiza a lista de centros e o CRP mostrado."""
        definir_opcoes(self.combo, self.escolha,
                       visoes.rotulos_centros(self.app.dados))
        self.mostrar_centro()

    def mostrar_centro(self):
        """Mostra tabela, sugestao e grafico do centro escolhido."""
        if not self.escolha.get():
            preencher(self.tabela, [])
            self.sugestao.set("Nenhum centro de trabalho cadastrado.")
            self.grafico.limpar()
            return
        dados = self.app.dados
        codigo = visoes.codigo_do_rotulo(self.escolha.get())
        preencher(self.tabela, visoes.linhas_crp(dados, codigo))
        self.sugestao.set(visoes.sugestao_crp(dados, codigo))
        self.grafico.mostrar(
            partial(graficos.figura_carga_capacidade, dados, codigo))


class AbaCustos:
    """Custo padrao dos itens fabricados (RF13)."""

    titulo = "Custos"

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        topo = ttk.Frame(self.quadro)
        topo.pack(fill="x", pady=(0, 8))
        botao(topo, "Gravar custo padrao como custo unitario",
              self.atualizar_custos)
        ttk.Label(topo, text="  (selecione um item para ver a composicao)"
                  ).pack(side="left")
        quadro, self.tabela = criar_tabela(self.quadro, [
            ("codigo", "Codigo", 90, "w"), ("descricao", "Descricao", 280,
                                            "w"),
            ("padrao", "Custo padrao (R$)", 140, "e"),
            ("cadastrado", "Custo cadastrado (R$)", 160, "e")], altura=8)
        quadro.pack(fill="x")
        self.tabela.bind("<<TreeviewSelect>>",
                         lambda _e: self.mostrar_detalhe())
        self.detalhe = tk.Text(self.quadro, height=14, wrap="none",
                               font=("Courier", 10), state="disabled")
        self.detalhe.pack(fill="both", expand=True, pady=(10, 0))

    def atualizar(self):
        """Recarrega a tabela de custos."""
        selecionado = valor_selecionado(self.tabela)
        preencher(self.tabela, visoes.linhas_custos(self.app.dados))
        if selecionado:
            for no in self.tabela.get_children():
                if str(self.tabela.item(no, "values")[0]) == selecionado:
                    self.tabela.selection_set(no)
                    break
        self.mostrar_detalhe()

    def mostrar_detalhe(self):
        """Mostra a composicao do custo do item selecionado."""
        codigo = valor_selecionado(self.tabela)
        self.detalhe.configure(state="normal")
        self.detalhe.delete("1.0", "end")
        if codigo is not None:
            linhas = custos.formatar_custo(self.app.dados, codigo)
            self.detalhe.insert("1.0", "\n".join(linhas))
        self.detalhe.configure(state="disabled")

    def atualizar_custos(self):
        """Grava o custo padrao como custo unitario dos fabricados."""
        if self.app.confirmar("O custo unitario dos itens PA e SA passara a "
                              "ser o custo padrao calculado. Continuar?"):
            self.app.tentar(
                lambda: custos.atualizar_custos_unitarios(self.app.dados),
                "Custos unitarios atualizados.")


class AbaRelatorios:
    """Exportacao CSV (RF14) e graficos de gestao (RF16)."""

    titulo = "Relatorios e graficos"
    GRAFICOS = ("Posicao de estoque", "Estoque projetado de um item",
                "Ordens por semana de entrega", "Carga x capacidade")

    def __init__(self, app, notebook):
        self.app = app
        self.quadro = ttk.Frame(notebook, padding=10)
        csv = ttk.LabelFrame(self.quadro, text="Exportar CSV (pasta saida/)",
                             padding=8)
        csv.pack(fill="x")
        botao(csv, "Posicao de estoque", self.exportar_estoque)
        botao(csv, "Lista de ordens", self.exportar_ordens)
        topo = ttk.LabelFrame(self.quadro, text="Graficos de gestao",
                              padding=8)
        topo.pack(fill="x", pady=8)
        self.tipo = tk.StringVar(value=self.GRAFICOS[0])
        combo = ttk.Combobox(topo, textvariable=self.tipo, width=32,
                             state="readonly", values=list(self.GRAFICOS))
        combo.pack(side="left", padx=(0, 8))
        combo.bind("<<ComboboxSelected>>", lambda _e: self.atualizar())
        self.alvo = tk.StringVar()
        self.combo_alvo = ttk.Combobox(topo, textvariable=self.alvo,
                                       width=38, state="readonly")
        self.combo_alvo.pack(side="left", padx=(0, 8))
        botao(topo, "Gerar grafico", self.gerar)
        botao(topo, "Salvar PNG", self.salvar)
        self.grafico = QuadroGrafico(self.quadro, largura=9, altura=4.2)
        self.grafico.quadro.pack(fill="both", expand=True)
        self.nome_arquivo = None

    def atualizar(self):
        """Atualiza a caixa de itens/centros conforme o grafico escolhido."""
        dados = self.app.dados
        tipo = self.tipo.get()
        if tipo == self.GRAFICOS[1]:
            opcoes = visoes.rotulos_itens(dados)
        elif tipo == self.GRAFICOS[3]:
            opcoes = visoes.rotulos_centros(dados)
        else:
            opcoes = []
        definir_opcoes(self.combo_alvo, self.alvo, opcoes)

    def exportar_estoque(self):
        """Exporta a posicao de estoque em CSV."""
        ok, caminho = self.app.consultar(
            lambda: relatorios.exportar_posicao_estoque(
                self.app.dados, persistencia.PASTA_SAIDA))
        if ok:
            self.app.aviso(f"Arquivo gerado:\n{caminho}", titulo="CSV")

    def exportar_ordens(self):
        """Exporta a lista de ordens em CSV."""
        ok, caminho = self.app.consultar(
            lambda: relatorios.exportar_ordens(
                self.app.dados, persistencia.PASTA_SAIDA))
        if ok:
            self.app.aviso(f"Arquivo gerado:\n{caminho}", titulo="CSV")

    def gerar(self):
        """Desenha o grafico escolhido na propria janela."""
        dados = self.app.dados
        tipo = self.tipo.get()
        codigo = visoes.codigo_do_rotulo(self.alvo.get())
        if tipo == self.GRAFICOS[0]:
            desenhar = partial(graficos.figura_posicao_estoque, dados)
            self.nome_arquivo = "grafico_posicao_estoque.png"
        elif tipo == self.GRAFICOS[1]:
            if not mrp.mrp_executado(dados):
                self.app.erro("Execute o MRP antes de gerar este grafico.")
                return
            desenhar = partial(graficos.figura_estoque_projetado, dados,
                               codigo)
            self.nome_arquivo = f"grafico_estoque_projetado_{codigo}.png"
        elif tipo == self.GRAFICOS[2]:
            desenhar = partial(graficos.figura_ordens_por_semana, dados)
            self.nome_arquivo = "grafico_ordens_por_semana.png"
        else:
            desenhar = partial(graficos.figura_carga_capacidade, dados,
                               codigo)
            self.nome_arquivo = f"grafico_carga_capacidade_{codigo}.png"
        if self.grafico.mostrar(desenhar):
            self.app.status.set("Grafico gerado.")

    def salvar(self):
        """Salva o grafico exibido em PNG na pasta saida/."""
        ok, caminho = self.app.consultar(
            lambda: self.grafico.salvar_png(self.nome_arquivo
                                            or "grafico.png"))
        if ok:
            self.app.aviso(f"Grafico salvo em:\n{caminho}", titulo="PNG")


def iniciar(dados):
    """Abre a janela principal e executa o laco de eventos."""
    Aplicacao(dados).executar()
