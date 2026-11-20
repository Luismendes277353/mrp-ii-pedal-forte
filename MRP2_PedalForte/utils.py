import os
import re
from datetime import datetime


def limpar_tela() -> None:
    os.system("clear" if os.name == "posix" else "cls")


def validar_codigo_item(codigo: str) -> bool:
    padrao = r"^(PA|SA|MP)-\d{3}$"
    return bool(re.match(padrao, codigo.strip().upper()))


def ler_texto_nao_vazio(mensagem: str) -> str:
    while True:
        valor = input(mensagem).strip()
        if valor:
            return valor
        print("ERRO: O campo não pode ficar vazio.")


def ler_float_positivo(mensagem: str, permitir_zero: bool = False) -> float:
    while True:
        entrada = input(mensagem).strip().replace(",", ".")
        try:
            valor = float(entrada)
            if permitir_zero and valor >= 0:
                return valor
            if not permitir_zero and valor > 0:
                return valor
            limite = "maior ou igual a zero" if permitir_zero else "maior que zero"
            print(f"ERRO: Informe um valor {limite}.")
        except ValueError:
            print("ERRO: Entrada numérica inválida.")


def ler_int_positivo(mensagem: str, permitir_zero: bool = False) -> int:
    while True:
        entrada = input(mensagem).strip()
        try:
            valor = int(entrada)
            if permitir_zero and valor >= 0:
                return valor
            if not permitir_zero and valor > 0:
                return valor
            limite = "maior ou igual a zero" if permitir_zero else "maior que zero"
            print(f"ERRO: Informe um número inteiro {limite}.")
        except ValueError:
            print("ERRO: Digite um número inteiro válido.")


def obter_data_atual() -> str:
    return datetime.now().strftime("%d/%m/%Y")