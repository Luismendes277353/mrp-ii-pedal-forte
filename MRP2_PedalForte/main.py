"""Ponto de entrada do sistema MRP II - Pedal Forte Bicicletas.

Uso::

    python main.py          # interface em modo texto
    python main.py --gui    # interface grafica (Tkinter, bonus)

Na primeira execucao, se a pasta data/ nao existir, a base de
demonstracao da fabrica ficticia e criada automaticamente (RNF09). Nas
demais, os dados sao carregados dos arquivos da pasta data/ (RF15).
"""

import sys

import menu
import persistencia


def configurar_console():
    """Garante saida UTF-8 (a arvore da BOM usa caracteres de desenho)."""
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def abrir_interface_grafica(dados):
    """Abre a interface grafica Tkinter; devolve o codigo de saida."""
    try:
        import gui
    except ImportError as erro:
        print(f"ERRO: Tkinter nao esta disponivel ({erro}).")
        print("No Linux instale com: sudo apt install python3-tk")
        print("Voce ainda pode usar o modo texto: python main.py")
        return 1
    try:
        gui.iniciar(dados)
    except gui.tk.TclError as erro:
        print(f"ERRO ao abrir a interface grafica: {erro}")
        print("Verifique se ha ambiente grafico (DISPLAY) disponivel.")
        return 1
    return 0


def main(argumentos=None):
    """Carrega os dados, abre a interface escolhida e grava ao sair."""
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    configurar_console()
    try:
        dados, base_criada = persistencia.inicializar()
    except persistencia.ErroPersistencia as erro:
        print(f"ERRO ao carregar os dados: {erro}")
        print("Corrija o arquivo indicado ou apague a pasta data/ para "
              "recriar a base de demonstracao.")
        return 1

    if base_criada:
        print("Base de demonstracao da Pedal Forte criada na pasta data/.")
    if "--gui" in argumentos:
        codigo = abrir_interface_grafica(dados)
        if codigo:
            return codigo
    else:
        try:
            menu.menu_principal(dados)
        except KeyboardInterrupt:
            print("\nEncerrando...")
    try:
        persistencia.salvar_tudo(dados)
    except persistencia.ErroPersistencia as erro:
        print(f"ERRO ao gravar os dados: {erro}")
        return 1
    print("Dados gravados. Ate logo!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
