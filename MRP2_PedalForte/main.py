from custos import atualizar_todos_custos_padrao
from menu import exibir_menu_principal
from persistencia import inicializar_base_demonstracao


def main() -> None:
    try:
        inicializar_base_demonstracao()
        atualizar_todos_custos_padrao()
        exibir_menu_principal()
    except KeyboardInterrupt:
        print("\nExecução interrompida pelo usuário. Dados salvos em data/.")


if __name__ == "__main__":
    main()