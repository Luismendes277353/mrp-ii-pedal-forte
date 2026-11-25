# Sistema MRP II - Pedal Forte Bicicletas

Sistema de Planejamento dos Recursos de Manufatura (MRP II) em Python para a fábrica fictícia **Pedal Forte Bicicletas Ltda.** (Divinópolis-MG): plano mestre de produção, estrutura de produto (BOM), estoques, MRP, ordens de produção e de compra, carga x capacidade (CRP), custo padrão, relatórios CSV e gráficos.

| | |
|---|---|
| **Aluno** | Luís Felipe Silva Mendes |
| **Matrícula** | 20263002367 |
| **Curso** | Engenharia de Computação - CEFET-MG, Campus Divinópolis |
| **Disciplina** | Programação em Python |
| **Professor** | Guido Pantuza |
| **Trabalho** | 2º - Sistema MRP II |
| **Repositório** | https://github.com/Luismendes277353/mrp-ii-pedal-forte |
| **Vídeo 1 (sistema em funcionamento)** | https://youtu.be/MstmdFY91y0 |
| **Vídeo 2 (código, arquitetura e decisões)** | https://youtu.be/BzUWqiOW7iM |

---

## 1. Requisitos e instalação

- **Python 3.10 ou superior.**
- **matplotlib** (gráficos). Todo o resto usa só a biblioteca padrão.
- **Tkinter** (apenas para a interface gráfica opcional). No Linux: `sudo apt install python3-tk`.
- Ambiente em que o sistema foi validado: Windows, Python 3.14.7.

```bash
git clone https://github.com/Luismendes277353/mrp-ii-pedal-forte.git
cd mrp-ii-pedal-forte/MRP2_PedalForte
pip install -r requirements.txt
```

## 2. Como executar

```bash
python main.py          # interface em modo texto (principal)
python main.py --gui    # interface gráfica Tkinter (bônus)
```

- Na **primeira execução**, se a pasta `data/` não existir, a base de demonstração da fábrica é criada automaticamente. Nas demais, os dados são carregados dos arquivos de `data/`.
- Para voltar à base de demonstração: menu **1 (Cadastros) > 5 (Restaurar base de demonstração)**, ou apague a pasta `data/` e execute de novo.
- Relatórios CSV e gráficos PNG são gravados em `saida/`. Sem ambiente gráfico (por exemplo, via SSH), os gráficos são apenas salvos em PNG, sem abrir janela.
- Em alguns sistemas Linux o comando é `python3` em vez de `python`.

## 3. Estrutura do projeto

```
mrp-ii-pedal-forte/
├── README.md                 # apresentação curta (aponta para este arquivo)
└── MRP2_PedalForte/
    ├── main.py               # ponto de entrada
    ├── menu.py               # menus e navegação (modo texto)
    ├── itens.py              # cadastro de itens
    ├── estrutura.py          # BOM e árvore indentada
    ├── estoque.py            # movimentações, saldo e kardex
    ├── mps.py                # plano mestre de produção
    ├── mrp.py                # cálculo MRP
    ├── ordens.py             # OPs, OCs e apontamento
    ├── capacidade.py         # centros, roteiros e CRP
    ├── custos.py             # custo padrão
    ├── relatorios.py         # exportação CSV
    ├── graficos.py           # gráficos de gestão (matplotlib)
    ├── persistencia.py       # leitura/gravação de arquivos e base demo
    ├── utils.py              # validações e formatação
    ├── previsao.py           # (bônus) previsão de demanda
    ├── visoes.py, gui.py     # (bônus) interface gráfica
    ├── requirements.txt
    ├── data/                 # itens, estrutura, estoque, centros, roteiros,
    │                         # mps, ordens, mrp, historico (.json) e movimentos.csv
    ├── saida/                # CSV e PNG gerados pelo sistema
    └── docs/README.md        # este arquivo
```

## 4. Instruções de uso

O menu principal tem as opções do mockup do enunciado, mais a **9 (Gráficos)**:

```
1. Cadastros (itens, estrutura, centros, roteiros)
2. Estoque (movimentar, saldo, kardex)
3. Plano Mestre de Producao (MPS)
4. Executar MRP
5. Ordens de producao e de compra
6. Carga x capacidade (CRP)
7. Custo padrao dos produtos
8. Relatorios (exportar CSV)
9. Graficos de gestao (matplotlib)
0. Sair
```

Digite o número da opção e `Enter`. Campos com valor entre colchetes aceitam `Enter` para usar o padrão; `Enter` em campo sem padrão cancela a operação. Números aceitam vírgula decimal e datas usam `dd/mm/aaaa`. Entradas inválidas mostram `ERRO: ...` e o sistema continua.

### Ciclo completo (exemplo com a base de demonstração recém-criada)

1. **MPS:** `3` > `1` para ver a demanda das 8 semanas.
2. **MRP:** `4` > `1`. Mostra as ordens planejadas e as mensagens de exceção; digite `SA-020` para ver o registro MRP do item e `Enter` para sair.
3. **Ordens:** `5`. Digite `F` e `OP-0006` (firmar), `L` e `OP-0006` (liberar), `A` e `OP-0006` (apontar a produção; `Enter` na data usa hoje).
4. **Rejeição por falta de componente:** repita `F`, `L`, `A` com `OP-0007`. O apontamento é recusado (faltam rodas montadas) e nada é alterado.
5. **Estoque atualizado:** `2` > `3` > `PA-001` mostra o kardex com a entrada do produto produzido.
6. **CRP e custo:** `6` mostra a sobrecarga do CT-03 nas semanas 3 e 6; `7` > `1` > `PA-001` mostra o custo padrão de R$ 792,60.

Os números das ordens (`OP-0006`, `OP-0007`) valem para a base de demonstração recém-criada com uma execução do MRP; se forem outros, use os que aparecem na tela.

## 5. Mapa de requisitos

### Funcionais

| Req. | O que faz | Onde está |
|---|---|---|
| RF01 | Menu principal | `menu.py` (`menu_principal`) |
| RF02 | Cadastrar, listar e alterar itens | `itens.py` (`cadastrar_item`, `listar_itens`, `alterar_item`) |
| RF03 | BOM em até 3 níveis e explosão indentada | `estrutura.py` (`adicionar_componente`, `montar_arvore`, `formatar_bom`) |
| RF04 | Movimentações de estoque | `estoque.py` (`registrar_movimento`) |
| RF05 | Saldo, kardex e alerta de segurança | `estoque.py` (`formatar_kardex`, `alerta_seguranca`) |
| RF06 | Centros de trabalho e roteiros | `capacidade.py` (`cadastrar_centro`, `definir_roteiro`) |
| RF07 | MPS de 8 semanas | `mps.py` (`definir_demanda`, `definir_plano`) |
| RF08 | Cálculo MRP e registro por item | `mrp.py` (`executar_mrp`, `formatar_registro`) |
| RF09 | Ordens planejadas (OP e OC) | `mrp.py`, `ordens.py` (`criar_ordem`) |
| RF10 | Firmar, liberar e encerrar ordens | `ordens.py` (`firmar_ordem`, `liberar_ordem`, `encerrar_ordem`) |
| RF11 | Apontamento de produção | `ordens.py` (`apontar_producao`) |
| RF12 | Carga x capacidade | `capacidade.py` (`analisar_centro`, `formatar_crp`) |
| RF13 | Custo padrão recursivo | `custos.py` (`custo_padrao`, `formatar_custo`) |
| RF14 | Exportação CSV | `relatorios.py` |
| RF15 | Persistência em `data/` | `persistencia.py` (`salvar_tudo`, `carregar_tudo`, `inicializar`) |
| RF16 | Gráficos com matplotlib | `graficos.py` (`grafico_*`) |

### Regras de negócio

| Regra | Onde está |
|---|---|
| RN01 código `Tipo-Número` único | `utils.validar_codigo_item`, `itens.cadastrar_item` |
| RN02 saldo nunca negativo | `estoque.calcular_variacao` |
| RN03 BOM com no máximo 3 níveis | `estrutura.validar_componente` (`TIPOS_PERMITIDOS`) |
| RN04 processamento PA, SA, MP | `mrp.ORDEM_DE_PROCESSAMENTO`, `mrp._demanda_dependente` |
| RN05 a RN07 necessidade líquida, lote mínimo e liberação | `mrp.calcular_registro` |
| RN08 só ordens firmes/liberadas são recebimentos | `ordens.apagar_planejadas`, `ordens.recebimentos_programados` |
| RN09 carga do centro | `capacidade.calcular_carga` |
| RN10 kardex imutável | `estoque.py` (não há função de excluir/editar; correção por ajuste) |

### Não funcionais

RNF02 Python 3.10+; RNF03 estilo PEP8; RNF04 módulos coesos; RNF05 tratamento de erros nos pontos de interação (`ErroNegocio` e funções `ler_*`); RNF07 persistência em JSON e CSV; RNF08 lógica de negócio própria, sem bibliotecas de ERP/MRP; RNF09 base de demonstração com 2 PA, 4 SA, 10 MP e 3 centros de trabalho; RNF10/RNF11 interface gráfica opcional (bônus).

## 6. Decisões de projeto

1. **Camadas.** `menu.py` e `gui.py` só leem dados, chamam funções de negócio e mostram resultados. Os módulos de regra (`itens`, `estrutura`, `estoque`, `mps`, `ordens`, `mrp`, `capacidade`, `custos`) **não têm `input()` nem `print()`**: recebem o dicionário `dados` e devolvem valores ou listas de texto (`formatar_*`). Isso permite testar a lógica sem interface.
2. **Estado em um dicionário.** Todo o sistema trabalha com um dicionário `dados` carregado do disco na inicialização e gravado após cada operação. Itens, centros e roteiros são dicionários indexados pelo código (busca direta e unicidade garantida); ordens e movimentos são listas (a ordem de registro importa).
3. **Erros por exceções.** `ErroNegocio` (regra violada ou entrada inválida), `OperacaoCancelada` (usuário desistiu) e `ErroPersistencia` (disco). O tratamento fica em um único ponto (`menu._executar_acao`), que mostra a mensagem e mantém o sistema de pé; erros inesperados são exibidos sem gravar.
4. **Validação de entradas** centralizada em `utils.py` (`ler_numero`, `ler_data`, `ler_codigo`...), incluindo rejeição de `nan`/`inf` e de datas impossíveis. As regras de negócio revalidam por conta própria.
5. **Recursão.** `estrutura.montar_arvore` (explosão da BOM) e `custos.custo_padrao` são recursivas. A RN03 (PA contém SA/MP, SA contém MP) garante que a BOM não tem ciclos; `montar_arvore` ainda tem uma trava de nível para dados corrompidos.
6. **MRP como função pura.** `mrp.calcular_registro` recebe só números e devolve o registro de um item; `executar_mrp` percorre PA, SA e MP e gera as ordens.
7. **Reserva de componentes.** Ordens FIRMES/LIBERADAS ainda não apontadas reservam seus componentes na semana de liberação, pois o consumo físico só ocorre no apontamento (RF11).
8. **Ordens atrasadas.** Liberação planejada antes da semana 1 gera ordem marcada como ATRASADA e uma mensagem de exceção (RN07). ATRASADA é uma marca de exibição, não um status: o ciclo continua PLANEJADA, FIRME, LIBERADA, ENCERRADA.
9. **Interpretação da RN09.** A carga do CRP considera as OPs abertas (planejadas, firmes e liberadas) com liberação nas semanas 1 a 8, o que permite planejar antes de liberar. Esta leitura reproduz o mockup de carga x capacidade do enunciado.
10. **Persistência.** JSON para estruturas e CSV para o kardex. A gravação é atômica por arquivo (escreve em `.tmp` e troca com `os.replace`). Ao carregar, o tipo de cada arquivo é conferido. A base de demonstração é criada pelas próprias funções de negócio, então já nasce válida e consistente (saldo igual à soma dos movimentos).
11. **Datas e números.** Datas ficam em ISO (`aaaa-mm-dd`) nos dados e aparecem como `dd/mm/aaaa`; valores usam vírgula decimal na tela e são arredondados em 4 casas para evitar erros de ponto flutuante.
12. **matplotlib sob demanda.** `graficos.py` separa preparação de dados, desenho em uma `Figure` e salvamento/exibição. O matplotlib só é importado quando um gráfico é pedido; sem ele, o resto do sistema funciona.

## 7. Base de demonstração

Criada em `data/` na primeira execução: 16 itens (2 PA, 4 SA, 10 MP), 3 centros de trabalho, 6 roteiros, MPS de 2 produtos acabados, 26 semanas de histórico de demanda, 25 movimentos de estoque e 8 ordens. O kardex do MP-202 (entrada de 60, saída de 40 por OP, ajuste de -2, saldo 18) e o registro MRP do SA-020 reproduzem os mockups do enunciado.

## 8. Extras

- **Previsão de demanda (IA).** `previsao.py` implementa do zero cinco modelos de séries temporais (ingênuo, média móvel, suavização exponencial, Holt e regressão linear), ajusta os parâmetros por busca em grade, escolhe o modelo de menor erro em semanas reservadas para teste e sugere a demanda das próximas 8 semanas, com faixa de ~80%. Acesso: menu **3 > 4**. O resultado só vai para o MPS se o usuário confirmar.
- **Interface gráfica.** `python main.py --gui` abre uma janela Tkinter com abas (painel, itens, BOM, estoque, MPS, previsão, MRP, ordens, CRP, custos, relatórios e gráficos), reutilizando as mesmas regras do modo texto.
- **Gráficos (RF16).** Posição de estoque, estoque projetado de um item, ordens por semana de entrega (barras empilhadas OP/OC) e carga x capacidade, exibidos na tela e salvos em `saida/`.

## 9. Validação e testes

- Estilo: verificado com flake8, sem avisos.
- Execução: ciclo completo no menu de texto (MPS, MRP, firmar/liberar ordens, apontamento e estoque atualizado), CRP, custo padrão, exportação CSV, gráficos e interface gráfica, no Windows com Python 3.14.7.

## 10. Limitações conhecidas

- A demanda de componentes das ordens atrasadas (liberação antes da semana 1) não entra no cálculo de liberações planejadas, e essas ordens não contam carga no CRP. Isso acompanha os mockups do enunciado, mas é uma simplificação.
- A gravação é atômica por arquivo, não para o conjunto dos arquivos de `data/`.
- O menu grava os dados após qualquer ação, inclusive consultas.
- A faixa de confiança da previsão tem largura constante nas 8 semanas.

## 11. Uso de inteligência artificial

- Utilizei ferramentas de IA apenas como apoio na correção de estilo (PEP 8), na padronização de comentários e docstrings e na estruturação deste README.
- A lógica do sistema, a organização dos módulos e a implementação foram desenvolvidas por mim, e sou capaz de explicar e alterar qualquer parte do código.
- A previsão de demanda (`previsao.py`) é um recurso do sistema (extra de IA/aprendizado de máquina), implementado do zero, e não deve ser confundida com o uso de ferramentas de IA no desenvolvimento.