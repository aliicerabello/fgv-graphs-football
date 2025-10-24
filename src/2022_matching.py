from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

print("ANALISE DE REDES - PASSES DECISIVOS")
print("ARGENTINA vs FRANCA - FINAL COPA 2022\n")

final_match_id = 3869685

try:
    events = sb.events(match_id=final_match_id)
    argentina_passes = events[(events['type'] == 'Pass') & (events['team'] == 'Argentina')].copy()
    franca_passes = events[(events['type'] == 'Pass') & (events['team'] == 'France')].copy()
    print(f"Passes Argentina: {len(argentina_passes)}, Franca: {len(franca_passes)}")
except Exception as e:
    print(f"Erro: {e}")
    argentina_passes = franca_passes = pd.DataFrame()

def identificar_passes_decisivos(passes_df, team_name, all_events):
    passes_decisivos = []
    chutes_time = all_events[(all_events['type'] == 'Shot') & (all_events['team'] == team_name)]
    
    for idx, passe in passes_df.iterrows():
        is_decisivo = False
        
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

def leads_to_shot(passe, chutes_time):
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

def criar_grafo_matriz(passes_decisivos):
    if not passes_decisivos:
        return None, pd.DataFrame()
    
    G = nx.DiGraph()
    df = pd.DataFrame(passes_decisivos)
    conexoes = df.groupby(['player', 'pass_recipient']).size().reset_index(name='weight')
    
    for _, row in conexoes.iterrows():
        G.add_edge(row['player'], row['pass_recipient'], weight=row['weight'])
    
    nodes = sorted(G.nodes())
    matriz = pd.DataFrame(0, index=nodes, columns=nodes)
    
    for u, v, data in G.edges(data=True):
        matriz.loc[u, v] = data['weight']
    
    return G, matriz

def visualizar_grafo(G, team_name, filename):
    if G.number_of_nodes() == 0:
        return
    
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    degrees = dict(G.degree(weight='weight'))
    max_degree = max(degrees.values()) if degrees else 1
    node_colors = [degrees[node] / max_degree for node in G.nodes()]
    
    nx.draw_networkx_nodes(G, pos, node_size=300, node_color=node_colors, 
                          cmap='Reds', alpha=0.8, edgecolors='black')
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=15, alpha=0.6)
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
    
    plt.title(f"REDE DE PASSES DECISIVOS - {team_name.upper()}")
    plt.axis('off')
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()

# Processamento principal
argentina_decisivos = identificar_passes_decisivos(argentina_passes, "Argentina", events)
franca_decisivos = identificar_passes_decisivos(franca_passes, "Franca", events)

print(f"Passes decisivos: Argentina {len(argentina_decisivos)}, Franca {len(franca_decisivos)}")

G_arg, matriz_arg = criar_grafo_matriz(argentina_decisivos)
G_fra, matriz_fra = criar_grafo_matriz(franca_decisivos)

# Salvar matrizes
if not matriz_arg.empty:
    matriz_arg.to_csv('matriz_adjacencia_argentina.csv')
    print("Matriz Argentina salva")
if not matriz_fra.empty:
    matriz_fra.to_csv('matriz_adjacencia_franca.csv')
    print("Matriz Franca salva")

# Visualizar grafos
visualizar_grafo(G_arg, "Argentina", "grafo_argentina.png")
visualizar_grafo(G_fra, "Franca", "grafo_franca.png")

print("ANALISE CONCLUIDA")