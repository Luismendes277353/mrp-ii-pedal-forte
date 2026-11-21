# 🚲 Sistema MRP II — Pedal Forte Bicicletas (GPTech Sistemas)

Sistema de Planejamento dos Recursos de Manufatura (**MRP II**) desenvolvido em Python 3.10+ para a fábrica fictícia **Pedal Forte Bicicletas Ltda.** (Divinópolis-MG), contemplando Plano Mestre de Produção (MPS), Estrutura de Produto multinível (BOM), Controle de Estoques e Kardex, Cálculo MRP, Gestão de Ordens (OP/OC), Planejamento de Capacidade (CRP), Custos Padrão, Relatórios CSV, Gráficos Matplotlib, Previsão de Demanda com IA e Interface Gráfica.

---

## 🛠️ Requisitos e Execução em Linux

### 1. Dependências
- **Python 3.10 ou superior**
- **Matplotlib** (para gráficos gerenciais — `RF16`)
- **Tkinter** (para a interface gráfica opcional — `RNF11`)

```bash
pip install matplotlib
# Caso o Tkinter não esteja instalado no Linux (Ubuntu/Debian):
sudo apt-get install python3-tk