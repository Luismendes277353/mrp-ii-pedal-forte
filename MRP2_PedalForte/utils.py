"""Funcoes utilitarias: validacao de entradas e formatacao de saidas.

Todas as leituras feitas no teclado passam por este modulo, de modo que o
restante do sistema receba apenas valores ja validados (RNF05).
"""

import math
import re
from datetime import date, datetime

HORIZONTE = 8
TIPOS_ITEM = ("PA", "SA", "MP")
TIPOS_FABRICADOS = ("PA", "SA")
LARGURA_TELA = 50
CASAS_DECIMAIS = 4

_PADRAO_CODIGO_ITEM = re.compile(r"^(PA|SA|MP)-\d{3,}$")
_PADRAO_CODIGO_CENTRO = re.compile(r"^CT-\d{2,}$")


class ErroNegocio(Exception):
    """Violacao de regra de negocio ou entrada invalida."""


class OperacaoCancelada(Exception):
    """O usuario cancelou a operacao deixando um campo vazio."""


def arredondar(valor):
    """Arredonda para evitar erros de ponto flutuante (e o zero negativo)."""
    return round(float(valor), CASAS_DECIMAIS) + 0.0


def converter_numero(texto):
    """Converte texto (aceita virgula decimal) em float."""
    limpo = str(texto).strip().replace(",", ".")
    try:
        valor = float(limpo)
    except ValueError:
        raise ErroNegocio(f"'{texto}' nao e um numero valido.") from None
    if math.isnan(valor) or math.isinf(valor):
        raise ErroNegocio(f"'{texto}' nao e um numero valido.")
    return valor


def converter_inteiro(texto):
    """Converte texto em inteiro, rejeitando valores fracionarios."""
    valor = converter_numero(texto)
    if valor != int(valor):
        raise ErroNegocio(f"'{texto}' deve ser um numero inteiro.")
    return int(valor)


def validar_numero(valor, nome, minimo=None, maior_que=None):
    """Valida limites numericos; retorna o proprio valor."""
    if minimo is not None and valor < minimo:
        raise ErroNegocio(
            f"{nome} deve ser maior ou igual a {formatar_numero(minimo)}.")
    if maior_que is not None and valor <= maior_que:
        raise ErroNegocio(
            f"{nome} deve ser maior que {formatar_numero(maior_que)}.")
    return valor


def validar_codigo_item(codigo):
    """Valida o formato Tipo-Numero (RN01) e devolve o codigo normalizado."""
    codigo = str(codigo).strip().upper()
    if not _PADRAO_CODIGO_ITEM.match(codigo):
        raise ErroNegocio(
            f"codigo '{codigo}' invalido. Use o formato Tipo-Numero, "
            "com tipo PA, SA ou MP (ex.: PA-001, SA-020, MP-201).")
    return codigo


def validar_codigo_centro(codigo):
    """Valida o formato de codigo de centro de trabalho (ex.: CT-03)."""
    codigo = str(codigo).strip().upper()
    if not _PADRAO_CODIGO_CENTRO.match(codigo):
        raise ErroNegocio(
            f"codigo '{codigo}' invalido. Use o formato CT-NN (ex.: CT-03).")
    return codigo


def validar_semana(semana):
    """Garante que a semana esta dentro do horizonte de planejamento."""
    if not isinstance(semana, int) or not 1 <= semana <= HORIZONTE:
        raise ErroNegocio(
            f"semana invalida. Informe um valor de 1 a {HORIZONTE}.")
    return semana


def converter_data(texto):
    """Converte dd/mm/aaaa em data ISO (aaaa-mm-dd)."""
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        raise ErroNegocio(
            f"data '{texto}' invalida. Use o formato dd/mm/aaaa.") from None


def validar_data_iso(texto):
    """Valida uma data ja no formato ISO."""
    try:
        return date.fromisoformat(str(texto)).isoformat()
    except ValueError:
        raise ErroNegocio(f"data '{texto}' invalida.") from None


def hoje_iso():
    """Data de hoje no formato ISO."""
    return date.today().isoformat()


def _perguntar(rotulo, padrao=None):
    sufixo = "" if padrao is None else f" [{padrao}]"
    texto = input(f">> {rotulo}{sufixo}: ").strip()
    if texto == "":
        if padrao is None:
            raise OperacaoCancelada()
        return str(padrao)
    return texto


def ler_texto(rotulo, padrao=None):
    """Le um texto nao vazio."""
    return _perguntar(rotulo, padrao)


def ler_numero(rotulo, minimo=None, maior_que=None, padrao=None,
               diferente_de_zero=False):
    """Le um numero real, repetindo a pergunta ate receber um valor valido."""
    texto_padrao = None if padrao is None else formatar_numero(padrao)
    while True:
        texto = _perguntar(rotulo, texto_padrao)
        try:
            valor = converter_numero(texto)
            validar_numero(valor, rotulo, minimo, maior_que)
            if diferente_de_zero and valor == 0:
                raise ErroNegocio(f"{rotulo} nao pode ser zero.")
            return valor
        except ErroNegocio as erro:
            print(f"ERRO: {erro}")


def ler_inteiro(rotulo, minimo=None, maior_que=None, padrao=None,
                maximo=None):
    """Le um numero inteiro, repetindo a pergunta ate receber um valido."""
    texto_padrao = None if padrao is None else str(padrao)
    while True:
        texto = _perguntar(rotulo, texto_padrao)
        try:
            valor = converter_inteiro(texto)
            validar_numero(valor, rotulo, minimo, maior_que)
            if maximo is not None and valor > maximo:
                raise ErroNegocio(
                    f"{rotulo} deve ser menor ou igual a {maximo}.")
            return valor
        except ErroNegocio as erro:
            print(f"ERRO: {erro}")


def ler_codigo(rotulo="Codigo do item", padrao=None, opcional=False):
    """Le e valida um codigo de item. Se opcional, vazio devolve None."""
    while True:
        try:
            texto = _perguntar(rotulo, padrao)
        except OperacaoCancelada:
            if opcional:
                return None
            raise
        try:
            return validar_codigo_item(texto)
        except ErroNegocio as erro:
            print(f"ERRO: {erro}")


def ler_codigo_centro(rotulo="Codigo do centro", padrao=None):
    """Le e valida um codigo de centro de trabalho."""
    while True:
        texto = _perguntar(rotulo, padrao)
        try:
            return validar_codigo_centro(texto)
        except ErroNegocio as erro:
            print(f"ERRO: {erro}")


def ler_opcao(rotulo, validas, padrao=None):
    """Le uma opcao de uma letra/palavra dentre `validas` (maiusculas)."""
    while True:
        texto = _perguntar(rotulo, padrao).upper()
        if texto in validas:
            return texto
        print(f"ERRO: opcao invalida. Escolha entre: {', '.join(validas)}.")


def ler_data(rotulo="Data", padrao_iso=None):
    """Le uma data dd/mm/aaaa e devolve no formato ISO."""
    padrao = None if padrao_iso is None else formatar_data(padrao_iso)
    while True:
        texto = _perguntar(rotulo + " (dd/mm/aaaa)", padrao)
        try:
            return converter_data(texto)
        except ErroNegocio as erro:
            print(f"ERRO: {erro}")


def confirmar(pergunta):
    """Pergunta sim/nao. Retorna True para 's'."""
    while True:
        resposta = input(f">> {pergunta} [s/n]: ").strip().lower()
        if resposta in ("s", "sim"):
            return True
        if resposta in ("n", "nao", "não", ""):
            return False
        print("ERRO: responda com 's' ou 'n'.")


def formatar_numero(valor, casas=3):
    """Formata numero com virgula decimal, sem zeros desnecessarios."""
    valor = round(float(valor), casas) + 0.0
    if valor == int(valor):
        return str(int(valor))
    return f"{valor:.{casas}f}".rstrip("0").replace(".", ",")


def formatar_decimal(valor, casas=1):
    """Formata numero com quantidade fixa de casas e virgula decimal."""
    return f"{valor:.{casas}f}".replace(".", ",")


def formatar_moeda(valor):
    """Formata valor monetario no padrao brasileiro (1.234,56)."""
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_data(data_iso):
    """Converte data ISO em dd/mm/aaaa (vazio se nao houver data)."""
    if not data_iso:
        return ""
    return datetime.strptime(data_iso, "%Y-%m-%d").strftime("%d/%m/%Y")


def formatar_quantidade_sinal(valor):
    """Quantidade com sinal explicito para o kardex (+60, -40)."""
    texto = formatar_numero(valor)
    return f"+{texto}" if valor > 0 else texto


def imprimir_titulo(texto):
    """Imprime um titulo entre linhas de '='."""
    print("=" * LARGURA_TELA)
    print(texto)
    print("=" * LARGURA_TELA)


def montar_tabela(cabecalho, linhas, alinhamentos=None, espaco=2):
    """Monta uma tabela de texto com colunas alinhadas.

    `alinhamentos` e uma string com '<' ou '>' para cada coluna.
    Devolve uma lista de strings (cabecalho + linhas).
    """
    alinhamentos = alinhamentos or "<" * len(cabecalho)
    textos = [[str(celula) for celula in linha] for linha in linhas]
    larguras = [len(str(titulo)) for titulo in cabecalho]
    for linha in textos:
        for i, celula in enumerate(linha):
            larguras[i] = max(larguras[i], len(celula))

    def montar(linha):
        """Formata uma linha da tabela respeitando larguras e alinhamentos."""
        partes = [f"{celula:{alinhamentos[i]}{larguras[i]}}"
                  for i, celula in enumerate(linha)]
        return (" " * espaco).join(partes).rstrip()

    return [montar(cabecalho)] + [montar(linha) for linha in textos]
