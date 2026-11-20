import os
import matplotlib.pyplot as plt
from capacidade import calcular_carga_semanal_centro
from mrp import calcular_mrp
from persistencia import carregar_json

PASTA_GRAFICOS = "docs"


def _exibir_e_salvar(caminho: str) -> None: