from capacidade import (
    cadastrar_centro_trabalho,
    cadastrar_roteiro,
    exibir_crp,
    listar_centros_trabalho,
    listar_roteiros,
)
from custos import atualizar_todos_custos_padrao, exibir_custo_padrao
from estoque import consultar_kardex, exibir_posicao_estoque, movimentar_estoque
from estrutura import cadastrar_componente_bom, exibir_estrutura
from graficos import menu_graficos
from itens import alterar_item, cadastrar_item, listar_itens
from mps import cadastrar_alterar_mps, exibir_mps
from mrp import executar_e_exibir_mrp
from ordens import gerenciar_ordens
from relatorios import exportar_todos_relatorios
from ia_demanda import executar_previsao_ia_cli

def _submenu_cadastros() -> None:
    while True:
        print("\n--- CADASTROS (ITENS, ESTRUTURA, CENTROS, ROTEIROS) ---")
        print("1. Cadastrar item (PA, SA, MP)")
        print("2. Listar itens")
        print("3. Alterar item")
        print("4. Cadastrar componente na estrutura (BOM)")
        print("5. Exibir estrutura de produto (explosão BOM)")
        print("6. Cadastrar centro de trabalho")
        print("7. Listar centros de trabalho")
        print("8. Cadastrar roteiro de fabricação")
        print("9. Listar roteiros de fabricação")
        print("0. Voltar")

        opcao = input("Escolha uma opcao: ").strip()
        match opcao:
            case "1":
                cadastrar_item()
            case "2":
                listar_itens()
            case "3":
                alterar_item()
                atualizar_todos_custos_padrao()
            case "4":
                cadastrar_componente_bom()
                atualizar_todos_custos_padrao()
            case "5":
                exibir_estrutura()
            case "6":
                cadastrar_centro_trabalho()
            case "7":
                listar_centros_trabalho()
            case "8":
                cadastrar_roteiro()
                atualizar_todos_custos_padrao()
            case "9":
                listar_roteiros()
            case "0":
                break
            case _:
                print("Opcao invalida.")


def _submenu_estoque() -> None:
    while True:
        print("\n--- GESTÃO DE ESTOQUES ---")
        print("1. Movimentar estoque (Entrada / Saída / Ajuste)")
        print("2. Consultar saldo e Kardex de um item")
        print("3. Exibir posição consolidada de estoque")
        print("0. Voltar")

        opcao = input("Escolha uma opcao: ").strip()
        match opcao:
            case "1":
                movimentar_estoque()
            case "2":
                consultar_kardex()
            case "3":
                exibir_posicao_estoque()
            case "0":
                break
            case _:
                print("Opcao invalida.")


def _submenu_mps() -> None:
    while True:
        print("\n--- PLANO MESTRE DE PRODUÇÃO (MPS) ---")
        print("1. Exibir MPS (8 semanas)")
        print("2. Cadastrar / Alterar demanda do MPS")
        print("3. [IA] Prever demanda automaticamente (Tendência + Sazonalidade)")
        print("0. Voltar")

        opcao = input("Escolha uma opcao: ").strip()
        match opcao:
            case "1":
                exibir_mps()
            case "2":
                cadastrar_alterar_mps()
            case "3":
                executar_previsao_ia_cli()
            case "0":
                break
            case _:
                print("Opcao invalida.")


def exibir_menu_principal() -> None:
    while True:
        print("\n" + "=" * 50)
        print("MRP II - PEDAL FORTE BICICLETAS")
        print("=" * 50)
        print("1. Cadastros (itens, estrutura, centros, roteiros)")
        print("2. Estoque (movimentar, saldo, kardex)")
        print("3. Plano Mestre de Producao (MPS)")
        print("4. Executar MRP")
        print("5. Ordens de producao e de compra")
        print("6. Carga x capacidade (CRP)")
        print("7. Custo padrao dos produtos")
        print("8. Relatorios (exportar CSV)")
        print("9. Graficos de gestao (matplotlib)")
        print("0. Sair")
        print("-" * 50)

        opcao = input("Escolha uma opcao: ").strip()
        match opcao:
            case "1":
                _submenu_cadastros()
            case "2":
                _submenu_estoque()
            case "3":
                _submenu_mps()
            case "4":
                executar_e_exibir_mrp()
            case "5":
                gerenciar_ordens()
            case "6":
                exibir_crp()
            case "7":
                exibir_custo_padrao()
            case "8":
                exportar_todos_relatorios()
            case "9":
                menu_graficos()
            case "0":
                print("Encerrando o sistema MRP II - Pedal Forte Bicicletas.")
                break
            case _:
                print("Opcao invalida. Tente novamente.")