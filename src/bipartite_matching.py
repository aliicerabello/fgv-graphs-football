import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

# --- Funções Auxiliares de Geometria ---


def calcular_distancia(p1, p2):
    """Calcula a distância euclidiana entre dois pontos (x, y)."""
    # Acessa as coordenadas [x, y]
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# --- Função Principal de Matching 360 ---


def identificar_defensor_mais_proximo_360(shot_event, team_defensor):
    """
    Identifica o defensor adversário mais próximo do atacante (origem do chute) 
    usando a coluna 'freeze_frame' aninhada no evento 'shot'.
    """

    # Tenta acessar o freeze_frame aninhado (que você confirmou existir no Shot)
    freeze_frame = shot_event.get('shot', {}).get('freeze_frame')

    if not freeze_frame:
        return None

    # Posição do atacante (origem do chute)
    atacante_pos = shot_event.get('location', [0, 0])

    min_distance = float('inf')
    defensor_mais_proximo = None

    for player_data in freeze_frame:
        # Verifica se o jogador NÃO é companheiro de equipe E não é o goleiro (que está sempre lá)
        is_opponent = not player_data.get('teammate', True)
        is_goalkeeper = player_data.get(
            'position', {}).get('name') == 'Goalkeeper'

        if is_opponent and not is_goalkeeper:
            defensor_pos = player_data['location']
            distancia = calcular_distancia(atacante_pos, defensor_pos)

            if distancia < min_distance:
                min_distance = distancia
                defensor_mais_proximo = player_data['player']['name']

    return defensor_mais_proximo


def criar_grafo_max_proximidade_360(events, team_atacante, team_defensor):
    """
    Cria um grafo bipartido de confronto com pesos baseados na frequência de 
    ser o defensor mais próximo do atacante em cada chute.
    """
    G = nx.Graph()
    confrontos = []

    # 1. Filtra eventos de Shot com dados de freeze_frame disponíveis
    shots_com_360 = events[
        (events['type'] == 'Shot') &
        (events['team'] == team_atacante) &
        (events['shot'].apply(lambda x: isinstance(x, dict)
         and 'freeze_frame' in x and x['freeze_frame'] is not None))
    ].copy()

    if shots_com_360.empty:
        print(
            f"Aviso: Nenhuma finalização de {team_atacante} com dados 360 (freeze_frame) encontrada.")
        return G

    # 2. Itera sobre os chutes e encontra o defensor mais próximo (o ideal match)
    for _, shot in shots_com_360.iterrows():
        atacante = shot['player']
        defensor_ideal = identificar_defensor_mais_proximo_360(
            shot, team_defensor)

        if defensor_ideal:
            confrontos.append((atacante, defensor_ideal))

    # 3. Constrói o Grafo Bipartido
    df_confrontos = pd.DataFrame(confrontos, columns=['atacante', 'defensor'])
    # Agrupamos a contagem (o peso)
    conexao_counts = df_confrontos.groupby(
        ['atacante', 'defensor']).size().reset_index(name='weight')

    A_nodes = set(df_confrontos['atacante'])
    B_nodes = set(df_confrontos['defensor'])

    # O atributo 'bipartite' é essencial para o layout e para identificar os conjuntos
    G.add_nodes_from(A_nodes, bipartite=0)  # Conjunto Atacante
    G.add_nodes_from(B_nodes, bipartite=1)  # Conjunto Defensor

    for _, row in conexao_counts.iterrows():
        G.add_edge(row['atacante'], row['defensor'], weight=row['weight'])

    return G

# --- Função de Análise e Visualização ---


def encontrar_defensor_ideal(G):
    """
    Para cada atacante, encontra o defensor com o qual ele teve a maior frequência de confronto (o ideal).
    """
    if G is None or G.number_of_nodes() == 0:
        return {}

    ideal_match = {}

    # Tenta identificar os nós atacantes
    atacantes = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 0}

    for atacante in atacantes:
        max_weight = -1
        defensor_ideal = None

        # Iterar sobre todos os vizinhos do atacante (os defensores)
        for defensor in G.neighbors(atacante):
            weight = G[atacante][defensor]['weight']
            if weight > max_weight:
                max_weight = weight
                defensor_ideal = defensor

        if defensor_ideal:
            ideal_match[atacante] = (defensor_ideal, max_weight)

    return ideal_match


def visualizar_grafo_bipartido(G, team_atacante, team_defensor, filename):
    """
    Visualiza o grafo bipartido de confronto Atacante vs Defensor.
    """
    if G is None or G.number_of_nodes() == 0:
        print(
            f"Não é possível visualizar o grafo para {team_atacante} vs {team_defensor}: Grafo vazio.")
        return

    plt.figure(figsize=(12, 10))

    # 1. Definir os dois conjuntos de nós
    nodes_A = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 0}
    nodes_B = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 1}

    # 2. Usar o layout bipartido para melhor visualização
    pos = nx.bipartite_layout(G, nodes_A, scale=1.5, aspect_ratio=0.5)

    # 3. Desenhar Nós e Arestas
    weights = [G[u][v]['weight'] for u, v in G.edges()]
    max_weight = max(weights) if weights else 1
    # Largura da linha proporcional à frequência
    edge_widths = [w / max_weight * 5 for w in weights]

    # Desenhar atacantes (Laranja) e defensores (Azul)
    nx.draw_networkx_nodes(G, pos, nodelist=nodes_A, node_color='orange',
                           node_size=800, alpha=0.9, edgecolors='black')
    nx.draw_networkx_nodes(G, pos, nodelist=nodes_B, node_color='lightblue',
                           node_size=800, alpha=0.9, edgecolors='black')

    # Desenhar arestas
    nx.draw_networkx_edges(G, pos, width=edge_widths,
                           edge_color='gray', alpha=0.7)

    # Desenhar rótulos
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold')

    plt.title(
        f"REDE DE MATCHING (Proximidade em Chutes) - {team_atacante} (Atq) vs {team_defensor} (Def)", fontsize=14)
    plt.axis('off')
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()

# Opcional: Adicionar a função de visualização da Matriz para debug


def visualizar_matriz_adjacencia(matriz, team_name, filename):
    plt.figure(figsize=(10, 10))
    plt.imshow(matriz, cmap='Reds', aspect='auto')
    plt.colorbar(label='Contagem de Passes Decisivos')
    plt.xticks(range(len(matriz.columns)),
               matriz.columns, rotation=90, fontsize=8)
    plt.yticks(range(len(matriz.index)), matriz.index, fontsize=8)
    plt.title(
        f"MATRIZ DE ADJACÊNCIA - PASSES DECISIVOS {team_name}", fontsize=14)
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()
