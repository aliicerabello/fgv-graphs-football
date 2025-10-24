from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import math

print("ANÁLISE DE REDES - PASSES DECISIVOS & MATCHING AVANÇADO (DUELOS)")
print("ARGENTINA vs FRANÇA - FINAL COPA 2022\n")

final_match_id = 3869685
PITCH_X_MAX = 120
PITCH_Y_MAX = 80

try:
    events = sb.events(match_id=final_match_id)
    argentina_passes = events[(events['type'] == 'Pass') & (
        events['team'] == 'Argentina')].copy()
    franca_passes = events[(events['type'] == 'Pass') &
                           (events['team'] == 'France')].copy()
    print(
        f"Passes Argentina: {len(argentina_passes)}, França: {len(franca_passes)}")
except Exception as e:
    print(f"Erro ao carregar dados do StatsBomb: {e}")
    argentina_passes = franca_passes = events = pd.DataFrame()


# ------------------------------------------------
# --- 1. FUNÇÕES DE REDE DE PASSES DECISIVOS ---
# ------------------------------------------------

def leads_to_shot(passe, chutes_time):
    # Verifica se o passe leva a um chute em até 5 segundos
    if chutes_time.empty:
        return False
    passe_segundos = passe['minute'] * 60 + passe['second']
    for _, chute in chutes_time.iterrows():
        chute_segundos = chute['minute'] * 60 + chute['second']
        if 0 < (chute_segundos - passe_segundos) <= 5:
            if ('possession' in passe and 'possession' in chute and
                    passe['possession'] == chute['possession']):
                return True
    return False


def is_passe_muito_progressivo(passe):
    # Verifica se o passe avança muito no campo adversário
    if 'pass_length' in passe and 'pass_end_location' in passe and passe['pass_end_location']:
        try:
            start_x = passe['location'][0] if 'location' in passe and passe['location'] else 0
            end_x = passe['pass_end_location'][0]
            progressao_x = end_x - start_x
            if progressao_x > 20 and end_x > 80:
                return True
        except:
            pass
    return False


def identificar_passes_decisivos(passes_df, team_name, all_events):
    # Combina todos os seus critérios para definir um passe decisivo
    passes_decisivos = []
    chutes_time = all_events[(all_events['type'] == 'Shot') & (
        all_events['team'] == team_name)].copy()

    for idx, passe in passes_df.iterrows():
        is_decisivo = False

        # Critérios de Passes Decisivos
        if 'pass_goal_assist' in passe and passe['pass_goal_assist'] is True:
            is_decisivo = True
        elif 'pass_shot_assist' in passe and passe['pass_shot_assist'] is True:
            is_decisivo = True
        elif 'pass_through_ball' in passe and passe['pass_through_ball'] is True:
            is_decisivo = True
        elif 'pass_cross' in passe and passe['pass_cross'] is True:
            is_decisivo = True
        elif 'play_pattern' in passe and passe['play_pattern'] == 'Counter Attack':
            is_decisivo = True
        elif leads_to_shot(passe, chutes_time):
            is_decisivo = True
        elif is_passe_muito_progressivo(passe):
            is_decisivo = True

        if is_decisivo and pd.notna(passe['pass_recipient']):
            passes_decisivos.append({
                'player': passe['player'],
                'pass_recipient': passe['pass_recipient'],
                'team': team_name
            })

    return passes_decisivos


def criar_grafo_matriz(passes_decisivos):
    # Cria o grafo de passes e a matriz de adjacência (usada no seu original)
    if not passes_decisivos:
        return None, pd.DataFrame()

    G = nx.DiGraph()
    df = pd.DataFrame(passes_decisivos)
    conexoes = df.groupby(['player', 'pass_recipient']
                          ).size().reset_index(name='weight')

    for _, row in conexoes.iterrows():
        G.add_edge(row['player'], row['pass_recipient'], weight=row['weight'])

    nodes = sorted(G.nodes())
    matriz = pd.DataFrame(0, index=nodes, columns=nodes)

    for u, v, data in G.edges(data=True):
        matriz.loc[u, v] = data['weight']

    return G, matriz


def visualizar_grafo(G, team_name, filename):
    # Função de visualização de rede de passes (sua função original)
    if G is None or G.number_of_nodes() == 0:
        print(
            f"Não é possível visualizar o grafo de passes para {team_name.upper()}: Grafo vazio.")
        return

    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    degrees = dict(G.degree(weight='weight'))
    max_degree = max(degrees.values()) if degrees else 1
    node_colors = [degrees[node] / max_degree for node in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_size=300, node_color=node_colors,
                           cmap='Reds', alpha=0.8, edgecolors='black')
    nx.draw_networkx_edges(G, pos, edge_color='gray',
                           arrows=True, arrowsize=15, alpha=0.6)
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')

    plt.title(f"REDE DE PASSES DECISIVOS - {team_name.upper()}")
    plt.axis('off')
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()


# -----------------------------------------------
# --- 2. FUNÇÕES DE MATCHING (SCORE DE VANTAGEM TÁTICA) ---
# -----------------------------------------------

def encontrar_driblador_desarmado(events, tackle_index, team_atacante):
    """Tenta identificar o atacante que foi desarmado imediatamente antes do tackle."""
    try:
        prev_event = events[events['index'] == tackle_index - 1].iloc[0]

        if prev_event['type'] == 'Dribble' and prev_event['team'] == team_atacante:
            if prev_event.get('dribble_outcome') != 'Complete':
                return prev_event['player']
    except (IndexError, KeyError, TypeError):
        pass
    return None


def criar_grafo_score_vantagem(events, team_atacante, team_defensor):
    """
    Cria um grafo bipartido de confrontos diretos comprovados com pesos de Score de Vantagem Tática.
    """
    G = nx.Graph()
    confrontos = []

    defensive_actions = events[
        (events['team'] == team_defensor) &
        (events['type'].isin(['Duel', 'Block', 'Interception', 'Ball Recovery']))
    ].copy()

    total_defensive_events = len(defensive_actions)

    for index, def_event in defensive_actions.iterrows():
        defensor = def_event['player']
        atacante = None
        score = 0

        # Heurística 1: TACKLE BEM-SUCEDIDO (+3)
        if def_event['type'] == 'Duel' and def_event.get('duel_type') == 'Tackle':
            atacante_driblador = encontrar_driblador_desarmado(
                events, def_event['index'], team_atacante)
            if atacante_driblador:
                atacante = atacante_driblador
                if def_event['duel_outcome'] == 'Won':
                    score = 3

        # Heurística 2: CHUTE BLOQUEADO (+2)
        elif def_event['type'] == 'Block':
            try:
                shot_event = events[
                    (events['type'] == 'Shot') &
                    (events['index'] == def_event['index'] - 1) &
                    (events['team'] == team_atacante)
                ].iloc[0]
                if shot_event.get('shot_outcome') == 'Blocked':
                    atacante = shot_event['player']
                    score = 2
            except (IndexError, KeyError, TypeError):
                pass

        # Heurística 3: INTERRUPÇÃO DE FLUXO/RECUPERAÇÃO DE BOLA (+1)
        elif def_event['type'] in ['Interception', 'Ball Recovery']:
            try:
                prev_event = events[events['index']
                                    == def_event['index'] - 1].iloc[0]
                if prev_event['team'] == team_atacante and prev_event['type'] == 'Pass' and prev_event.get('pass_outcome') in ['Incomplete', 'Out']:
                    atacante = prev_event['player']
                    score = 1
            except (IndexError, KeyError, TypeError):
                pass

        # Heurística 4: FALTA SOFRIDA PELO DEFENSOR (Forçar erro de agressão) (+1)
        elif def_event['type'] == 'Foul Won' and def_event['team'] == team_defensor:
            defensor = def_event['player']
            try:
                # Encontra o evento de 'Foul Committed' da equipe atacante
                related_foul = events[events['related_events'].apply(
                    lambda x: def_event['id'] in x if isinstance(x, list) else False)].iloc[0]
                if related_foul['team'] == team_atacante:
                    atacante = related_foul['player']
                    score = 1
            except (IndexError, KeyError):
                pass

        elif def_event['type'] == 'Pass' and def_event['team'] == team_atacante:
            if def_event.get('pass_end_location') and def_event.get('location'):

                start_x = def_event['location'][0]
                end_x = def_event['pass_end_location'][0]
                is_regressive = (end_x < start_x)  # Se a coordenada X diminuiu

                if is_regressive:
                    # Se for um passe regressivo, procuramos a ação defensiva imediatamente anterior.
                    try:
                        prev_event = events[events['index']
                                            == def_event['index'] - 1].iloc[0]
                        if prev_event['type'] in ['Pressure', 'Duel', 'Tackle'] and prev_event['team'] == team_defensor:
                            # Encontrado o defensor que forçou o passe regressivo.
                            defensor = prev_event['player']
                            atacante = def_event['player']
                            score = 1  # ANULAÇÃO TÁTICA (+1)
                    except (IndexError, KeyError, TypeError):
                        pass

        if (index + 1) % 100 == 0 or (index + 1) == total_defensive_events:
            print(
                f"-> Processando Defesa {team_defensor} ({index + 1}/{total_defensive_events} ações defensivas)...")

        if atacante and defensor and score > 0:
            confrontos.append((atacante, defensor, score))

    if not confrontos:
        print(
            f"Nenhum duelo de Score de Vantagem encontrado para {team_atacante} vs {team_defensor}.")
        return G

    df_confrontos = pd.DataFrame(
        confrontos, columns=['atacante', 'defensor', 'score'])
    conexao_score = df_confrontos.groupby(['atacante', 'defensor'])[
        'score'].sum().reset_index(name='weight')

    # Construção final do grafo bipartido
    A_nodes = set(conexao_score['atacante'])
    B_nodes = set(conexao_score['defensor'])

    G.add_nodes_from(A_nodes, bipartite=0)
    G.add_nodes_from(B_nodes, bipartite=1)

    for _, row in conexao_score.iterrows():
        G.add_edge(row['atacante'], row['defensor'], weight=row['weight'])

    print(
        f"Grafo Bipartido (Score de Vantagem) criado: {G.number_of_nodes()} nós e {G.number_of_edges()} arestas.")
    return G


def encontrar_defensor_ideal(G):
    """Identifica o defensor com o maior peso de Score de Vantagem para cada atacante."""
    if G is None or G.number_of_nodes() == 0:
        return {}

    ideal_match = {}
    atacantes = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 0}

    for atacante in atacantes:
        max_weight = -1
        defensor_ideal = None

        for defensor in G.neighbors(atacante):
            weight = G[atacante][defensor]['weight']
            if weight > max_weight:
                max_weight = weight
                defensor_ideal = defensor

        if defensor_ideal:
            ideal_match[atacante] = (defensor_ideal, max_weight)

    return ideal_match


# --- FUNÇÕES DE ANÁLISE E DESTAQUE ---

def encontrar_matching_perfeito(G):
    """
    Encontra o Matching de Peso Máximo (o conjunto de duelos de maior Score de Vantagem total)
    garantindo que cada jogador seja conectado a no máximo um adversário.
    """
    if G is None or G.number_of_nodes() == 0:
        return set()

    matching_arestas = nx.max_weight_matching(G, maxcardinality=False)

    return matching_arestas


def visualizar_grafo_bipartido(G, team_atacante, team_defensor, filename, matching_arestas):
    """
    Visualiza o grafo bipartido de confronto, destacando o Matching Perfeito.
    """
    if G is None or G.number_of_nodes() == 0:
        return

    plt.figure(figsize=(12, 10))

    nodes_A = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 0}
    nodes_B = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 1}

    pos = nx.bipartite_layout(G, nodes_A, scale=1.5, aspect_ratio=0.5)

    # Cores e tamanhos dos Nós (Padrão)
    nx.draw_networkx_nodes(G, pos, nodelist=nodes_A, node_color='orange',
                           node_size=800, alpha=0.9, edgecolors='black', label=f'{team_atacante} (Atacantes)')
    nx.draw_networkx_nodes(G, pos, nodelist=nodes_B, node_color='lightblue',
                           node_size=800, alpha=0.9, edgecolors='black', label=f'{team_defensor} (Defensores)')

    # Desenhar TODAS as arestas (em cinza, fundo)
    all_edges = G.edges()
    weights = [G[u][v]['weight'] for u, v in G.edges()]
    max_weight = max(weights) if weights else 1
    # Largura fina para arestas de fundo
    edge_widths = [w / max_weight * 1 for w in weights]

    nx.draw_networkx_edges(G, pos, edgelist=all_edges,
                           width=edge_widths, edge_color='lightgray', alpha=0.5)

    # Desenhar as ARESTAS DO MATCHING (em destaque, grossas e vermelhas)
    matching_edges = list(matching_arestas)
    matching_weights = [G[u][v]['weight'] for u, v in matching_edges]
    # Largura grossa para destaque
    matching_widths = [w / max_weight * 5 for w in matching_weights]

    nx.draw_networkx_edges(G, pos, edgelist=matching_edges, width=matching_widths,
                           edge_color='red', alpha=1.0, arrows=True, arrowsize=15)

    # Desenhar rótulos
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold')

    plt.title(
        f"REDE DE MATCHING (Score de Vantagem Tática) - {team_atacante} (Atq) vs {team_defensor} (Def)", fontsize=14)
    plt.axis('off')
    plt.legend(scatterpoints=1)
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()
# ---------------------------------------------
# --- PROCESSAMENTO PRINCIPAL E EXECUÇÃO ---
# ---------------------------------------------


if not events.empty:

    # 1. Análise de Redes de Passe Decisivos (Sua Original)
    argentina_decisivos = identificar_passes_decisivos(
        argentina_passes, "Argentina", events)
    franca_decisivos = identificar_passes_decisivos(
        franca_passes, "France", events)

    print(
        f"Passes decisivos: Argentina {len(argentina_decisivos)}, França {len(franca_decisivos)}")

    G_arg, matriz_arg = criar_grafo_matriz(argentina_decisivos)
    G_fra, matriz_fra = criar_grafo_matriz(franca_decisivos)

    # Salvar Matrizes
    if not matriz_arg.empty:
        matriz_arg.to_csv('matriz_adjacencia_argentina.csv')
    if not matriz_fra.empty:
        matriz_fra.to_csv('matriz_adjacencia_franca.csv')

    # Visualizar Grafos de Passes Decisivos
    visualizar_grafo(G_arg, "Argentina", "grafo_argentina.png")
    visualizar_grafo(G_fra, "França", "grafo_franca.png")

    # 2. Análise de Matching Bipartido (SCORE DE VANTAGEM TÁTICA)
print("\n--- ANÁLISE DE MATCHING (Score de Vantagem Tática) ---")

# Matching ARGENTINA (Atacante) vs FRANÇA (Defensor)
G_arg_fra_score = criar_grafo_score_vantagem(events, 'Argentina', 'France')

# Matching FRANÇA (Atacante) vs ARGENTINA (Defensor)
G_fra_arg_score = criar_grafo_score_vantagem(events, 'France', 'Argentina')

# --- NOVO: CÁLCULO DO MATCHING DE PESO MÁXIMO (O 'PERFEITO') ---
matching_arg_fra = encontrar_matching_perfeito(G_arg_fra_score)
matching_fra_arg = encontrar_matching_perfeito(G_fra_arg_score)

print("\n--- MATCHING DE PESO MÁXIMO (Duelos Mais Impactantes) ---")
print("Argentina (Atacantes) -> França (Defensores):")
for u, v in matching_arg_fra:
    peso = G_arg_fra_score[u][v]['weight']
    print(f"  {u} <-> {v} (Score: {peso})")

print("\nFrança (Atacantes) -> Argentina (Defensores):")
for u, v in matching_fra_arg:
    peso = G_fra_arg_score[u][v]['weight']
    print(f"  {u} <-> {v} (Score: {peso})")


# Visualizar os grafos bipartidos (PASSANDO O MATCHING PARA DESTAQUE)
visualizar_grafo_bipartido(G_arg_fra_score, 'Argentina', 'France',
                           'matching_score_arg_fra.png', matching_arg_fra)
visualizar_grafo_bipartido(G_fra_arg_score, 'France', 'Argentina',
                           'matching_score_fra_arg.png', matching_fra_arg)

print("\nANÁLISE CONCLUÍDA")
