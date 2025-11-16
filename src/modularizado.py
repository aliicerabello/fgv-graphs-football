from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import math

print("ANALISADOR DE REDES - STATSBOMB")
print("==================================\n")
#CÓDIGO FRANÇA X ARGENTINA: 3869685
#CÓDIGO MARROCOS X ESPANHA: 3869220

# A PESSOA COLOCA O ID DO JOGO AQUI 
MATCH_ID = int(input("Insira o ID do jogo no StatsBomb: "))

try:
    print(f"Buscando jogo ID: {MATCH_ID}...")
    
    # Puxa tudo automaticamente do StatsBomb
    events = sb.events(match_id=MATCH_ID)
    
    # Descobre os times sozinho
    times = [t for t in events['team'].dropna().unique() if t]
    time1, time2 = times[0], times[1]
    
    print(f" {time1} vs {time2}")

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
        
        plt.title(f"REDE DE PASSES DECISIVOS - {team_name.upper()}\nJogo ID: {MATCH_ID}")
        plt.axis('off')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.show()
    
    # Analisa cada time
    for time in [time1, time2]:
        print(f"\n Analisando {time}...")
        
        # Pega passes do time
        passes = events[(events['type'] == 'Pass') & (events['team'] == time)].copy()
        print(f"    {len(passes)} passes totais")
        
        # Identifica passes decisivos usando a mesma lógica do primeiro código
        passes_decisivos = identificar_passes_decisivos(passes, time, events)
        
        print(f"  {len(passes_decisivos)} passes decisivos")
        
        if not passes_decisivos:
            print("   Nenhum passe decisivo")
            continue
        
        # Cria grafo e matriz usando a mesma lógica do primeiro código
        G, matriz = criar_grafo_matriz(passes_decisivos)
        
        print(f"    {G.number_of_nodes()} jogadores, {G.number_of_edges()} conexões")
        
        # Acha jogador mais conectado
        graus = dict(G.degree(weight='weight'))
        top_jogador = max(graus.items(), key=lambda x: x[1])
        print(f"    Mais conectado: {top_jogador[0]} ({top_jogador[1]} conexões)")
        
        # Salva matriz
        matriz.to_csv(f"matriz_{time}_{MATCH_ID}.csv")
        print(f"    Matriz salva: matriz_{time}_{MATCH_ID}.csv")
        
        # Gera gráfico usando a mesma visualização do primeiro código
        visualizar_grafo(G, time, f"grafo_{time}_{MATCH_ID}.png")
        print(f"    Gráfico salvo: grafo_{time}_{MATCH_ID}.png")

    print(f"\n ANÁLISE CONCLUÍDA!")
    print(f" Arquivos gerados:")
    print(f"   - matriz_{time1}_{MATCH_ID}.csv")
    print(f"   - matriz_{time2}_{MATCH_ID}.csv") 
    print(f"   - grafo_{time1}_{MATCH_ID}.png")
    print(f"   - grafo_{time2}_{MATCH_ID}.png")

except Exception as e:
    print(f" ERRO: {e}")