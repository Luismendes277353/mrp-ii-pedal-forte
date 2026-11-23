"""Menus e navegacao do sistema (RF01) - interface em modo texto.

Este modulo concentra a interacao com o usuario: le os dados digitados
(sempre por meio das funcoes de validacao de ``utils``), chama as funcoes
de negocio dos demais modulos e imprime os resultados. Erros de regra de
negocio (``ErroNegocio``) sao exibidos sem interromper o sistema (RNF05).
Os dados sao gravados em arquivo apos cada operacao concluida (RF15).
"""

import capacidade
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
from utils import (
    HORIZONTE,
    LARGURA_TELA,
    TIPOS_ITEM,
    ErroNegocio,
    OperacaoCancelada,
    confirmar,
    formatar_moeda,
    formatar_numero,
    hoje_iso,
    imprimir_titulo,
    ler_codigo,
    ler_codigo_centro,
    ler_data,
    ler_inteiro,
    ler_numero,
    ler_opcao,
    ler_texto,
)


def _ler_escolha(rotulo="Escolha uma opcao"):
    """Le a escolha do menu; fim de entrada (EOF) equivale a sair."""
    try:
        return input(f"{rotulo}: ").strip().upper()
    except EOFError:
        return "0"


def _imprimir(linhas):
    """Imprime uma lista de linhas de texto."""
    for linha in linhas:
        print(linha)


def _salvar(dados):
    try:
        persistencia.salvar_tudo(dados)
    except persistencia.ErroPersistencia as erro:
        print(f"\nERRO ao gravar os dados: {erro}")


def _executar_acao(dados, acao):
    """Executa uma acao tratando erros e gravando os dados (RF15)."""
    try:
        acao(dados)
    except OperacaoCancelada:
        print("\nOperacao cancelada.")
    except ErroNegocio as erro:
        print(f"\nERRO: {erro}")
    except KeyboardInterrupt:
        print("\nOperacao interrompida.")
    except Exception as erro:  # ultima barreira: nunca derrubar o sistema
        print(f"\nERRO inesperado ({type(erro).__name__}): {erro}")
        return
    _salvar(dados)


def _executar_menu(dados, titulo, opcoes, rotulo_saida="Voltar"):
    """Exibe um menu numerado ate o usuario escolher sair/voltar.

    `opcoes` e uma lista de tuplas ``(rotulo, funcao)``; cada funcao recebe
    o dicionario de dados.
    """
    while True:
        print()
        imprimir_titulo(titulo)
        for numero, (rotulo, _) in enumerate(opcoes, start=1):
            print(f"{numero}. {rotulo}")
        print(f"0. {rotulo_saida}")
        print("-" * LARGURA_TELA)
        escolha = _ler_escolha()
        if escolha == "0":
            return
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            print()
            _executar_acao(dados, opcoes[int(escolha) - 1][1])
        else:
            print("Opcao invalida.")


def _caminho_curto(caminho):
    try:
        return caminho.relative_to(persistencia.RAIZ)
    except ValueError:
        return caminho


def _cadastrar_item(dados):
    imprimir_titulo("CADASTRAR ITEM")
    codigo = ler_codigo("Codigo do item (ex.: PA-001, SA-020, MP-201)")
    if codigo in dados["itens"]:
        raise ErroNegocio(f"ja existe um item com o codigo {codigo} (RN01).")
    descricao = ler_texto("Descricao")
    unidade = ler_texto("Unidade de medida", padrao="un")
    custo = ler_numero("Custo unitario (R$)", minimo=0, padrao=0)
    lead_time = ler_inteiro("Lead time (semanas)", minimo=0, padrao=1)
    seguranca = ler_numero("Estoque de seguranca", minimo=0, padrao=0)
    lote = ler_numero("Lote minimo", minimo=0, padrao=0)
    item = itens.cadastrar_item(dados, codigo, descricao, unidade, custo,
                                lead_time, seguranca, lote)
    print(f"\nItem {item['codigo']} cadastrado (tipo {item['tipo']}).")
    if itens.eh_fabricado(item):
        print("Lembrete: cadastre a estrutura (BOM) e o roteiro deste item.")


def _listar_itens(dados):
    tipo = ler_opcao("Tipo [T]odos, PA, SA ou MP", ("T",) + TIPOS_ITEM,
                     padrao="T")
    print()
    _imprimir(itens.formatar_itens(dados, None if tipo == "T" else tipo))


def _alterar_item(dados):
    imprimir_titulo("ALTERAR ITEM")
    item = itens.obter_item(dados, ler_codigo("Codigo do item"))
    print(f"{item['codigo']} - {item['descricao']} (tipo {item['tipo']}). "
          "Enter mantem o valor atual.")
    alteracoes = {
        "descricao": ler_texto("Descricao", padrao=item["descricao"]),
        "unidade": ler_texto("Unidade de medida", padrao=item["unidade"]),
        "custo_unitario": ler_numero(
            "Custo unitario (R$)", minimo=0, padrao=item["custo_unitario"]),
        "lead_time": ler_inteiro(
            "Lead time (semanas)", minimo=0, padrao=item["lead_time"]),
        "estoque_seguranca": ler_numero(
            "Estoque de seguranca", minimo=0,
            padrao=item["estoque_seguranca"]),
        "lote_minimo": ler_numero(
            "Lote minimo", minimo=0, padrao=item["lote_minimo"]),
    }
    itens.alterar_item(dados, item["codigo"], alteracoes)
    print(f"\nItem {item['codigo']} alterado.")


def _incluir_componente(dados):
    imprimir_titulo("INCLUIR COMPONENTE NA ESTRUTURA (BOM)")
    pai = ler_codigo("Codigo do item pai (PA ou SA)")
    itens.obter_item(dados, pai)
    componente = ler_codigo("Codigo do componente")
    quantidade = ler_numero("Quantidade por unidade do pai", maior_que=0)
    resultado = estrutura.adicionar_componente(dados, pai, componente,
                                               quantidade)
    print(f"\nComponente {componente} {resultado} na estrutura de {pai}.")


def _remover_componente(dados):
    imprimir_titulo("REMOVER COMPONENTE DA ESTRUTURA (BOM)")
    pai = ler_codigo("Codigo do item pai")
    componente = ler_codigo("Codigo do componente a remover")
    estrutura.remover_componente(dados, pai, componente)
    print(f"\nComponente {componente} removido da estrutura de {pai}.")


def _exibir_bom(dados):
    codigo = ler_codigo("Codigo do produto")
    print()
    _imprimir(estrutura.formatar_bom(dados, codigo))


def _cadastrar_centro(dados):
    imprimir_titulo("CADASTRAR CENTRO DE TRABALHO")
    codigo = ler_codigo_centro("Codigo do centro (ex.: CT-03)")
    descricao = ler_texto("Descricao")
    horas = ler_numero("Capacidade (horas/semana)", maior_que=0)
    custo_hora = ler_numero("Custo-hora (R$)", minimo=0)
    capacidade.cadastrar_centro(dados, codigo, descricao, horas, custo_hora)
    print(f"\nCentro {codigo} cadastrado.")


def _listar_centros(dados):
    _imprimir(capacidade.formatar_centros(dados))


def _alterar_centro(dados):
    imprimir_titulo("ALTERAR CENTRO DE TRABALHO")
    centro = capacidade.obter_centro(dados, ler_codigo_centro())
    print(f"{centro['codigo']} - {centro['descricao']}. "
          "Enter mantem o valor atual.")
    descricao = ler_texto("Descricao", padrao=centro["descricao"])
    horas = ler_numero("Capacidade (horas/semana)", maior_que=0,
                       padrao=centro["capacidade"])
    custo_hora = ler_numero("Custo-hora (R$)", minimo=0,
                            padrao=centro["custo_hora"])
    capacidade.alterar_centro(dados, centro["codigo"], descricao, horas,
                              custo_hora)
    print(f"\nCentro {centro['codigo']} alterado.")


def _definir_roteiro(dados):
    imprimir_titulo("DEFINIR ROTEIRO (operacao unica)")
    codigo = ler_codigo("Codigo do item fabricado (PA ou SA)")
    itens.obter_item(dados, codigo)
    print()
    _imprimir(capacidade.formatar_centros(dados))
    centro = ler_codigo_centro("Centro de trabalho que produz o item")
    atual = capacidade.obter_roteiro(dados, codigo)
    tempo = ler_numero("Tempo por unidade (horas)", maior_que=0,
                       padrao=atual["tempo_unitario"] if atual else None)
    capacidade.definir_roteiro(dados, codigo, centro, tempo)
    print(f"\nRoteiro de {codigo} definido: {centro}, "
          f"{formatar_numero(tempo)} h/un.")


def _listar_roteiros(dados):
    _imprimir(capacidade.formatar_roteiros(dados))
    sem_roteiro = capacidade.itens_fabricados_sem_roteiro(dados)
    if sem_roteiro:
        print(f"\nAtencao: itens fabricados sem roteiro: "
              f"{', '.join(sem_roteiro)}.")


def _restaurar_demo(dados):
    print("Isto substitui TODOS os dados atuais pela base de demonstracao "
          "da Pedal Forte.")
    if not confirmar("Confirma a restauracao"):
        raise OperacaoCancelada()
    novos = persistencia.gerar_base_demo()
    dados.clear()
    dados.update(novos)
    print("\nBase de demonstracao restaurada.")


def _menu_itens(dados):
    _executar_menu(dados, "CADASTRO DE ITENS", [
        ("Cadastrar item", _cadastrar_item),
        ("Listar itens", _listar_itens),
        ("Alterar item", _alterar_item),
    ])


def _menu_estrutura(dados):
    _executar_menu(dados, "ESTRUTURA DE PRODUTO (BOM)", [
        ("Incluir/atualizar componente", _incluir_componente),
        ("Remover componente", _remover_componente),
        ("Exibir estrutura indentada (explosao)", _exibir_bom),
    ])


def _menu_centros(dados):
    _executar_menu(dados, "CENTROS DE TRABALHO", [
        ("Cadastrar centro", _cadastrar_centro),
        ("Listar centros", _listar_centros),
        ("Alterar centro", _alterar_centro),
    ])


def _menu_roteiros(dados):
    _executar_menu(dados, "ROTEIROS DE PRODUCAO", [
        ("Definir roteiro de um item fabricado", _definir_roteiro),
        ("Listar roteiros", _listar_roteiros),
    ])


def _menu_cadastros(dados):
    _executar_menu(dados, "CADASTROS", [
        ("Itens", _menu_itens),
        ("Estrutura de produto (BOM)", _menu_estrutura),
        ("Centros de trabalho", _menu_centros),
        ("Roteiros", _menu_roteiros),
        ("Restaurar base de demonstracao", _restaurar_demo),
    ])


def _movimentar_estoque(dados):
    imprimir_titulo("MOVIMENTACAO DE ESTOQUE")
    item = itens.obter_item(dados, ler_codigo("Codigo do item"))
    atual = estoque.saldo(dados, item["codigo"])
    print(f"{item['codigo']} {item['descricao']} - saldo atual: "
          f"{formatar_numero(atual)} {item['unidade']}")
    letra = ler_opcao("Tipo [E]ntrada [S]aida [A]juste", ("E", "S", "A"))
    tipo = {"E": "ENTRADA", "S": "SAIDA", "A": "AJUSTE"}[letra]
    if tipo == "AJUSTE":
        quantidade = ler_numero("Quantidade (negativa reduz o saldo)",
                                diferente_de_zero=True)
    else:
        quantidade = ler_numero("Quantidade", maior_que=0)
    # Valida antes de pedir os demais dados (RN02): erro imediato.
    estoque.calcular_variacao(dados, item["codigo"], tipo, quantidade)
    data = ler_data("Data", padrao_iso=hoje_iso())
    documento = ler_texto("Documento/motivo (ex.: NF 4521 - Fornecedor)")
    movimento = estoque.registrar_movimento(
        dados, item["codigo"], tipo, quantidade, documento, data)
    print(f"\n{tipo} registrada. Novo saldo de {item['codigo']}: "
          f"{formatar_numero(movimento['saldo'])} {item['unidade']}.")
    alerta = estoque.alerta_seguranca(dados, item["codigo"])
    if alerta:
        print(alerta)


def _consultar_saldo(dados):
    item = itens.obter_item(dados, ler_codigo("Codigo do item"))
    atual = estoque.saldo(dados, item["codigo"])
    print(f"\n{item['codigo']} {item['descricao']}")
    print(f"Saldo atual: {formatar_numero(atual)} {item['unidade']}")
    print("Estoque de seguranca: "
          f"{formatar_numero(item['estoque_seguranca'])} {item['unidade']}")
    valor = atual * item["custo_unitario"]
    print(f"Valor em estoque: R$ {formatar_moeda(valor)}")
    alerta = estoque.alerta_seguranca(dados, item["codigo"])
    print(alerta if alerta else "Situacao: saldo dentro do estoque de "
                                "seguranca.")


def _consultar_kardex(dados):
    codigo = ler_codigo("Codigo do item")
    print()
    _imprimir(estoque.formatar_kardex(dados, codigo))


def _posicao_estoque(dados):
    imprimir_titulo("POSICAO DE ESTOQUE")
    _imprimir(estoque.formatar_posicao(dados))


def _menu_estoque(dados):
    _executar_menu(dados, "ESTOQUE", [
        ("Movimentar (entrada, saida, ajuste)", _movimentar_estoque),
        ("Consultar saldo de um item", _consultar_saldo),
        ("Kardex de um item", _consultar_kardex),
        ("Posicao de estoque (todos os itens)", _posicao_estoque),
    ])


def _exibir_mps(dados):
    imprimir_titulo(f"PLANO MESTRE DE PRODUCAO (horizonte de {HORIZONTE} "
                    "semanas)")
    _imprimir(mps.formatar_mps(dados))


def _alterar_demanda(dados):
    codigo = ler_codigo("Codigo do produto acabado (PA)")
    plano = mps.obter_plano(dados, codigo)
    semana = ler_inteiro(f"Semana (1 a {HORIZONTE})", minimo=1,
                         maximo=HORIZONTE)
    quantidade = ler_numero(
        f"Demanda da semana {semana}", minimo=0,
        padrao=plano[semana - 1])
    mps.definir_demanda(dados, codigo, semana, quantidade)
    print(f"\nDemanda de {codigo} na semana {semana}: "
          f"{formatar_numero(quantidade)}.")


def _cadastrar_plano(dados):
    codigo = ler_codigo("Codigo do produto acabado (PA)")
    itens.obter_item(dados, codigo)
    plano_atual = mps.obter_plano(dados, codigo)
    print("Informe a demanda de cada semana (Enter mantem o valor atual).")
    novo_plano = [
        ler_numero(f"Semana {semana}", minimo=0,
                   padrao=plano_atual[semana - 1])
        for semana in range(1, HORIZONTE + 1)
    ]
    mps.definir_plano(dados, codigo, novo_plano)
    print(f"\nMPS de {codigo} atualizado.")


def _prever_demanda(dados):
    imprimir_titulo("PREVISAO DE DEMANDA (IA)")
    codigo = ler_codigo("Codigo do produto acabado (PA)")
    resultado = previsao.prever_demanda_pa(dados, codigo)
    print()
    _imprimir(previsao.formatar_previsao(resultado))
    print()
    try:
        _informar_grafico(graficos.grafico_previsao(resultado))
    except ErroNegocio as erro:
        print(f"(grafico nao gerado: {erro})")
    if confirmar("Aplicar esta previsao como demanda do MPS"):
        previsao.aplicar_previsao_ao_mps(dados, resultado["codigo"],
                                         resultado)
        print(f"\nMPS de {resultado['codigo']} atualizado com a previsao. "
              "Execute o MRP para replanejar.")


def _exibir_historico(dados):
    codigo = ler_codigo("Codigo do produto acabado (PA)")
    historico = previsao.obter_historico(dados, codigo)
    if not historico:
        raise ErroNegocio(f"{codigo} ainda nao tem historico de demanda.")
    print(f"\nHistorico de demanda real de {codigo} "
          f"({len(historico)} semanas, da mais antiga para a mais recente):")
    print(", ".join(formatar_numero(valor) for valor in historico))


def _registrar_demanda_real(dados):
    codigo = ler_codigo("Codigo do produto acabado (PA)")
    quantidade = ler_numero("Demanda real da semana que acabou", minimo=0)
    previsao.adicionar_demanda_real(dados, codigo, quantidade)
    total = len(previsao.obter_historico(dados, codigo))
    print(f"\nDemanda registrada. {codigo} agora tem {total} semanas de "
          "historico.")


def _menu_mps(dados):
    _executar_menu(dados, "PLANO MESTRE DE PRODUCAO (MPS)", [
        ("Exibir MPS", _exibir_mps),
        ("Alterar a demanda de uma semana", _alterar_demanda),
        ("Cadastrar/alterar o plano completo de um PA (8 semanas)",
         _cadastrar_plano),
        ("Previsao de demanda de um PA (IA) e aplicar ao MPS",
         _prever_demanda),
        ("Registrar demanda real da semana (historico)",
         _registrar_demanda_real),
        ("Exibir historico de demanda de um PA", _exibir_historico),
    ])


def _exibir_registro(dados):
    codigo = ler_codigo("Codigo do item")
    print()
    _imprimir(mrp.formatar_registro(dados, codigo))


def _executar_mrp(dados):
    imprimir_titulo("EXECUCAO DO MRP")
    planejadas = len(ordens.listar_ordens(dados, status=ordens.PLANEJADA))
    if planejadas:
        print(f"As {planejadas} ordens PLANEJADAS atuais serao apagadas e "
              "recalculadas (RN08).")
    resumo = mrp.executar_mrp(dados)
    print()
    _imprimir(mrp.formatar_resumo(resumo, dados["mrp"]["executado_em"]))
    print("\nUse a opcao 5 do menu principal para firmar/liberar as ordens.")
    while True:
        codigo = ler_codigo(
            "Codigo de um item para ver o registro MRP (Enter para sair)",
            opcional=True)
        if codigo is None:
            return
        print()
        try:
            _imprimir(mrp.formatar_registro(dados, codigo))
        except ErroNegocio as erro:
            print(f"ERRO: {erro}")
        print()


def _exibir_excecoes(dados):
    if not mrp.mrp_executado(dados):
        raise ErroNegocio("o MRP ainda nao foi executado.")
    mensagens = dados["mrp"]["mensagens"]
    if not mensagens:
        print("Nenhuma mensagem de excecao na ultima execucao do MRP.")
        return
    print(f"{len(mensagens)} mensagens de excecao (ultima execucao):")
    _imprimir(f"  ! {mensagem}" for mensagem in mensagens)


def _menu_mrp(dados):
    _executar_menu(dados, "MRP - PLANEJAMENTO DE NECESSIDADES", [
        ("Executar MRP (gera as ordens planejadas)", _executar_mrp),
        ("Exibir registro MRP de um item", _exibir_registro),
        ("Exibir mensagens de excecao", _exibir_excecoes),
    ])


def _firmar_ordem(dados):
    numero = ler_texto("Numero da ordem (ex.: OP-0007)")
    ordem = ordens.firmar_ordem(dados, numero)
    print(f"\nOrdem {ordem['numero']} FIRMADA.")


def _firmar_todas(dados):
    total = len(ordens.listar_ordens(dados, status=ordens.PLANEJADA))
    if total == 0:
        raise ErroNegocio("nao ha ordens PLANEJADAS para firmar.")
    if not confirmar(f"Firmar as {total} ordens PLANEJADAS"):
        raise OperacaoCancelada()
    ordens.firmar_todas(dados)
    print(f"\n{total} ordens FIRMADAS.")


def _liberar_ordem(dados):
    numero = ler_texto("Numero da ordem (ex.: OP-0007)")
    ordem = ordens.liberar_ordem(dados, numero)
    print(f"\nOrdem {ordem['numero']} LIBERADA.")


def _apontar_producao(dados):
    numero = ler_texto("Numero da OP liberada (ex.: OP-0005)")
    ordem = ordens.obter_ordem(dados, numero)
    data = ler_data("Data do apontamento", padrao_iso=hoje_iso())
    ordens.apontar_producao(dados, ordem["numero"], data)
    item = itens.obter_item(dados, ordem["item"])
    print(f"\nProducao apontada: {ordem['numero']} ENCERRADA. "
          f"{formatar_numero(ordem['quantidade'])} {item['unidade']} de "
          f"{item['codigo']} entraram no estoque (saldo: "
          f"{formatar_numero(estoque.saldo(dados, item['codigo']))}).")


def _encerrar_ordem(dados):
    numero = ler_texto("Numero da ordem liberada (OP ou OC)")
    ordem = ordens.obter_ordem(dados, numero)
    data = ler_data("Data do encerramento", padrao_iso=hoje_iso())
    ordens.encerrar_ordem(dados, ordem["numero"], data)
    acao = "producao apontada" if ordem["tipo"] == "OP" else "compra recebida"
    print(f"\nOrdem {ordem['numero']} ENCERRADA ({acao}).")


def _menu_ordens(dados):
    mostrar_todas = False
    comandos = {
        "F": _firmar_ordem,
        "L": _liberar_ordem,
        "A": _apontar_producao,
        "E": _encerrar_ordem,
        "T": _firmar_todas,
    }
    while True:
        print()
        if mostrar_todas:
            imprimir_titulo("ORDENS - todas (inclusive encerradas)")
            lista = ordens.listar_ordens(dados)
        else:
            imprimir_titulo("ORDENS ABERTAS (nao encerradas)")
            lista = ordens.listar_ordens(dados, abertas=True)
        _imprimir(ordens.formatar_ordens(lista))
        print("\n[F] Firmar  [L] Liberar  [A] Apontar producao  "
              "[E] Encerrar/receber OC")
        print("[T] Firmar todas  [H] Historico (alternar)  [V] Voltar")
        escolha = _ler_escolha()
        if escolha in ("V", "0"):
            return
        if escolha == "H":
            mostrar_todas = not mostrar_todas
        elif escolha in comandos:
            print()
            _executar_acao(dados, comandos[escolha])
        else:
            print("Opcao invalida.")


def _exibir_crp(dados):
    if not dados["centros"]:
        raise ErroNegocio("nenhum centro de trabalho cadastrado.")
    _imprimir(capacidade.formatar_centros(dados))
    print()
    texto = ler_texto("Codigo do centro (Enter = todos)", padrao="TODOS")
    if texto.strip().upper() == "TODOS":
        codigos = sorted(dados["centros"])
    else:
        codigos = [capacidade.obter_centro(dados, texto)["codigo"]]
    for codigo in codigos:
        print()
        _imprimir(capacidade.formatar_crp(dados, codigo))
    print("\nA carga considera as OPs abertas (planejadas, firmes e "
          f"liberadas) liberadas nas semanas 1 a {HORIZONTE} (RN09).")
    sem_roteiro = capacidade.itens_fabricados_sem_roteiro(dados)
    if sem_roteiro:
        print("Atencao: itens fabricados sem roteiro nao geram carga: "
              f"{', '.join(sem_roteiro)}.")


def _custo_de_um_item(dados):
    codigo = ler_codigo("Codigo do item fabricado (PA ou SA)")
    print()
    _imprimir(custos.formatar_custo(dados, codigo))


def _tabela_de_custos(dados):
    imprimir_titulo("CUSTO PADRAO DOS ITENS FABRICADOS")
    _imprimir(custos.formatar_tabela_custos(dados))


def _atualizar_custos(dados):
    print("O custo unitario cadastrado dos itens PA e SA passara a ser o "
          "custo padrao calculado.")
    if not confirmar("Confirma a atualizacao"):
        raise OperacaoCancelada()
    total = custos.atualizar_custos_unitarios(dados)
    print(f"\n{total} itens atualizados.")


def _menu_custos(dados):
    _executar_menu(dados, "CUSTO PADRAO", [
        ("Custo padrao de um item fabricado (detalhado)", _custo_de_um_item),
        ("Custo padrao de todos os itens fabricados", _tabela_de_custos),
        ("Atualizar custo unitario dos fabricados com o custo padrao",
         _atualizar_custos),
    ])


def _exportar_estoque(dados):
    caminho = relatorios.exportar_posicao_estoque(dados)
    print(f"Posicao de estoque exportada em: {_caminho_curto(caminho)}")


def _exportar_ordens(dados):
    caminho = relatorios.exportar_ordens(dados)
    print(f"Lista de ordens exportada em: {_caminho_curto(caminho)}")


def _exportar_tudo(dados):
    _exportar_estoque(dados)
    _exportar_ordens(dados)


def _menu_relatorios(dados):
    _executar_menu(dados, "RELATORIOS (exportar CSV)", [
        ("Exportar posicao de estoque", _exportar_estoque),
        ("Exportar lista de ordens", _exportar_ordens),
        ("Exportar ambos", _exportar_tudo),
    ])


def _informar_grafico(resultado):
    caminho, exibido = resultado
    print(f"Grafico salvo em: {_caminho_curto(caminho)}")
    if not exibido:
        print("(sem ambiente grafico disponivel: o grafico foi apenas salvo "
              "em PNG)")


def _grafico_estoque(dados):
    _informar_grafico(graficos.grafico_posicao_estoque(dados))


def _grafico_projetado(dados):
    if not mrp.mrp_executado(dados):
        raise ErroNegocio("execute o MRP antes de gerar este grafico.")
    codigo = ler_codigo("Codigo do item")
    _informar_grafico(graficos.grafico_estoque_projetado(dados, codigo))


def _grafico_ordens(dados):
    _informar_grafico(graficos.grafico_ordens_por_semana(dados))


def _grafico_carga(dados):
    _imprimir(capacidade.formatar_centros(dados))
    codigo = ler_codigo_centro("Codigo do centro de trabalho")
    _informar_grafico(graficos.grafico_carga_capacidade(dados, codigo))


def _menu_graficos(dados):
    _executar_menu(dados, "GRAFICOS DE GESTAO (matplotlib)", [
        ("Posicao de estoque (saldo x estoque de seguranca)",
         _grafico_estoque),
        ("Estoque projetado de um item (8 semanas do MRP)",
         _grafico_projetado),
        ("Ordens de producao e de compra por semana de entrega",
         _grafico_ordens),
        ("Carga x capacidade de um centro de trabalho", _grafico_carga),
    ])


def menu_principal(dados):
    """Exibe o menu principal ate o usuario escolher sair."""
    _executar_menu(dados, "MRP II - PEDAL FORTE BICICLETAS", [
        ("Cadastros (itens, estrutura, centros, roteiros)", _menu_cadastros),
        ("Estoque (movimentar, saldo, kardex)", _menu_estoque),
        ("Plano Mestre de Producao (MPS)", _menu_mps),
        ("Executar MRP", _menu_mrp),
        ("Ordens de producao e de compra", _menu_ordens),
        ("Carga x capacidade (CRP)", _exibir_crp),
        ("Custo padrao dos produtos", _menu_custos),
        ("Relatorios (exportar CSV)", _menu_relatorios),
        ("Graficos de gestao (matplotlib)", _menu_graficos),
    ], rotulo_saida="Sair")
