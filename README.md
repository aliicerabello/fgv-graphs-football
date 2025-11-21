# Análise Computacional de Estratégias Coletivas no Futebol

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](#)
[![NetworkX](https://img.shields.io/badge/NetworkX-Graphs-yellow.svg)](#)
[![Status](https://img.shields.io/badge/Status-Research-orange.svg)](#)

## Sobre o Projeto

Este projeto aplica conceitos de **Teoria dos Grafos** para análise computacional de estratégias coletivas no futebol, utilizando dados reais da plataforma **StatsBomb**.  
Os jogadores são representados como vértices e os passes decisivos como arestas direcionadas e ponderadas, permitindo identificar padrões táticos e estruturas ofensivas e defensivas.

### Estudos de Caso Analisados

- **Argentina 3 x 3 França** — Final da Copa do Mundo 2022  
- **Marrocos 0 x 0 Espanha** — Oitavas de Final da Copa do Mundo 2022

---

## Como Executar

### Pré-requisitos

- Python 3.8+
- Git

### Instalação

```bash
git clone https://github.com/aliicerabello/fgv-graphs-football
cd fgv-graphs-football
```

### Execução

```bash
cd src
python main.py
```
Após rodar o comando acima, o terminal solicitará o ID da partida.
Você pode digitar um ID manualmente ou digitar "s" para usar um ID aleatório da Copa do Mundo 2022.


## Exemplo de Uso


```
SISTEMA INTEGRADO DE ANÁLISE STATSBOMB
Usar ID aleatório? (s/n): n
Insira o ID do jogo no StatsBomb: 3869220

--- Análise de Rede de Passes ---
 Morocco vs Spain

Analisando Morocco...
   Jogador mais conectado: Walid Cheddira (4 conexões)
   Arquivos salvos:
     - data/Morocco_vs_Spain/matriz_passes_Morocco_3869220.csv
     - figures/Morocco_vs_Spain/grafo_passes_Morocco_3869220.png

Analisando Spain...
   Jogador mais conectado: Álvaro Borja Morata Martín (6 conexões)
   Arquivos salvos:
     - data/Morocco_vs_Spain/matriz_passes_Spain_3869220.csv
     - figures/Morocco_vs_Spain/grafo_passes_Spain_3869220.png
```
---

## Estrutura do Projeto

```
fgv-graphs-football/

├── report/
│   ├── relatorio.pdf
│   └── relatorio.tex
├── src/
│   ├── main.py
│   ├── passes.py
│   ├── matching.py
│   └── find_id.py
├── data/
|   ├── Argentina_vs_France/
|       ├── graus_passes_Argentina_3869685.csv
|       ├── graus_passes_France_3869685.csv
│       ├── matriz_passes_Argentina_3869685.csv
│       ├── matriz_passes_France_3869685.csv
│       ├── matriz_matching_Argentina_France.csv
│       └── matriz_matching_France_Argentina.csv
│   ├── Morocco_vs_Spain/
|       ├── graus_passes_Morocco_3869220.csv
|       ├── graus_passes_Spain_3869685.csv
│       ├── matriz_passes_Morocco_3869220.csv
│       ├── matriz_passes_Spain_3869220.csv
│       ├── matriz_matching_Morocco_Spain.csv
│       └── matriz_matching_Spain_Morocco.csv
└── figures/
|   ├── Argentina_vs_France/
│       ├── grafo_passes_France_3869685.png
│       ├── grafo_passes_Argentina_3869685.png
│       ├── grafo_matching_Argentina_France_3869685.png
│       └── grafo_matching_France_Argentina_3869685.png
|   ├── Morocco_vs_Spain/
│       ├── grafo_passes_Morocco_3869220.png
│       ├── grafo_passes_Spain_3869220.png
│       ├── grafo_matching_Morocco_Spain_3869220.png
│       └── grafo_matching_Spain_Morocco_3869220.png
└──
```
---

## Funcionalidades
### Análise de Redes de Passes

- Identificação de passes decisivos;
- Cálculo de graus de entrada e saída;
- Geração de matrizes de adjacência em CSV;
- Visualização de grafos das redes coletivas.

### Análise de Matchings Defensivos

- Identificação de confrontos diretos entre atacantes e defensores;
- Cálculo de matchings máximos ponderados utilizando NetworkX;
- Identificação dos duelos mais relevantes.

### Métricas Calculadas

- Grau de centralidade dos jogadores;
- Densidade da rede de passes;
- Matchings defensivos mais relevantes;
- Padrões ofensivos e defensivos.

---
## IDs de Exemplo
```
3869685 — Argentina vs França

3869220 — Marrocos vs Espanha
```
---

## Dependências

```bash
statsbombpy
pandas
networkx
matplotlib
numpy
```
---

## Resultados e Análises

O relatório completo (relatorio.pdf) inclui:

- Análise quantitativa dos graus dos vértices;
- Visualizações das redes de passes e matchings defensivos;
- Interpretação dos padrões táticos identificados;
- Comparação entre filosofias de jogo;
- Validação metodológica com múltiplos casos.

---

## Autores

- Alice Rabello Oliveira
- Pablo Levy Fernandes Alcântara
- Raul Medici Martinelli

---


















