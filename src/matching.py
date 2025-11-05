from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns

print("ANALISADOR DE MATCHING - STATSBOMB APERFEIÇOADO")
print("==============================================\n")

MATCH_ID = int(input("Insira o ID do jogo no StatsBomb: "))

try:
    print(f"Buscando jogo ID: {MATCH_ID}...")
    events = sb.events(match_id=MATCH_ID)

    times = [t for t in events['team'].dropna().unique() if t]
    time1, time2 = times[0], times[1]
    print(f" {time1} vs {time2}")

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
            (events['type'].isin(
                ['Duel', 'Block', 'Interception', 'Ball Recovery', 'Foul Won']))
        ].copy()

        total_defensive_events = len(defensive_actions)

        for index, def_event in defensive_actions.iterrows():
            defensor = def_event['player']
            atacante = None
            score = 0

            # Métrica 1: TACKLE BEM-SUCEDIDO (+3)
            if def_event['type'] == 'Duel' and def_event.get('duel_type') == 'Tackle':
                atacante_driblador = encontrar_driblador_desarmado(
                    events, def_event['index'], team_atacante)
                if atacante_driblador:
                    atacante = atacante_driblador
                    if def_event.get('duel_outcome') == 'Won':
                        score = 3

            # Métrica 2: CHUTE BLOQUEADO (+2)
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

            # Métrica 3: INTERRUPÇÃO DE FLUXO/RECUPERAÇÃO DE BOLA (+1)
            elif def_event['type'] in ['Interception', 'Ball Recovery']:
                try:
                    prev_event = events[events['index']
                                        == def_event['index'] - 1].iloc[0]
                    if prev_event['team'] == team_atacante and prev_event['type'] == 'Pass' and prev_event.get('pass_outcome') in ['Incomplete', 'Out']:
                        atacante = prev_event['player']
                        score = 1
                except (IndexError, KeyError, TypeError):
                    pass

            # Métrica 4: FALTA SOFRIDA PELO DEFENSOR (Forçar erro de agressão) (+1)
            elif def_event['type'] == 'Foul Won' and def_event['team'] == team_defensor:
                defensor = def_event['player']
                try:
                    related_foul = events[events['related_events'].apply(
                        lambda x: def_event['id'] in x if isinstance(x, list) else False)].iloc[0]
                    if related_foul['team'] == team_atacante:
                        atacante = related_foul['player']
                        score = 1
                except (IndexError, KeyError):
                    pass

            # Métrica 5: PASSE REGRESSIVO FORÇADO (+1)
            elif def_event['type'] == 'Pass' and def_event['team'] == team_atacante:
                if def_event.get('pass_end_location') and def_event.get('location'):
                    start_x = def_event['location'][0]
                    end_x = def_event['pass_end_location'][0]
                    is_regressive = (end_x < start_x)

                    if is_regressive:
                        try:
                            prev_event = events[events['index']
                                                == def_event['index'] - 1].iloc[0]
                            if prev_event['team'] == team_defensor and prev_event['type'] in ['Pressure', 'Duel', 'Tackle']:
                                defensor = prev_event['player']
                                atacante = def_event['player']
                                score = 1
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

        # Construção do grafo bipartido
        A_nodes = set(conexao_score['atacante'])
        B_nodes = set(conexao_score['defensor'])

        G.add_nodes_from(A_nodes, bipartite=0)
        G.add_nodes_from(B_nodes, bipartite=1)

        for _, row in conexao_score.iterrows():
            G.add_edge(row['atacante'], row['defensor'], weight=row['weight'])

        print(
            f"Grafo Bipartido (Score de Vantagem) criado: {G.number_of_nodes()} nós e {G.number_of_edges()} arestas.")
        return G

    def encontrar_matching_perfeito(G):
        """
        Encontra o Matching de Peso Máximo garantindo que cada jogador seja conectado a no máximo um adversário.
        """
        if G is None or G.number_of_nodes() == 0 or G.number_of_edges() == 0:
            print("Grafo vazio ou sem arestas. Retornando conjunto vazio.")
            return set()

        try:
            matching_arestas = nx.max_weight_matching(G, maxcardinality=False)
            return matching_arestas
        except Exception as e:
            print(f"Erro no matching: {e}")
            return set()

    def criar_matriz_adjacencia(G, team_atacante, team_defensor, match_id):
        """Cria matriz de adjacência em CSV para análise detalhada"""
        if G is None or G.number_of_edges() == 0:
            return None

        # Extrai nós de cada time
        atacantes = [n for n, d in G.nodes(
            data=True) if d.get('bipartite') == 0]
        defensores = [n for n, d in G.nodes(
            data=True) if d.get('bipartite') == 1]

        matriz = pd.DataFrame(0, index=atacantes, columns=defensores)

        for u, v, data in G.edges(data=True):
            if u in atacantes and v in defensores:
                matriz.loc[u, v] = data['weight']
            elif v in atacantes and u in defensores:
                matriz.loc[v, u] = data['weight']

        csv_filename = f"matriz_adjacencia_{team_atacante}_{team_defensor}_{match_id}.csv"
        matriz.to_csv(csv_filename, encoding='utf-8-sig')
        print(f"Matriz de adjacência salva: {csv_filename}")

        return matriz

    def visualizar_grafo_aprimorado(G, team_atacante, team_defensor, filename, matching_arestas):
        """Visualização APRIMORADA do grafo bipartido"""
        if G is None or G.number_of_nodes() == 0:
            return

        plt.figure(figsize=(20, 12))

        nodes_A = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 0}
        nodes_B = {n for n, d in G.nodes(data=True) if d.get('bipartite') == 1}

        pos = nx.bipartite_layout(G, nodes_A, scale=2.0, aspect_ratio=1.2)

        for node, (x, y) in pos.items():
            if node in nodes_A:
                pos[node] = (x - 1.5, y)
            else:
                pos[node] = (x + 1.5, y)

        # Nós atacantes (laranja)
        nx.draw_networkx_nodes(G, pos, nodelist=nodes_A,
                               node_color='#FF6B35', node_size=1200,
                               edgecolors='black', linewidths=2, alpha=0.9)

        # Nós defensores (azul)
        nx.draw_networkx_nodes(G, pos, nodelist=nodes_B,
                               node_color='#004E89', node_size=1200,
                               edgecolors='black', linewidths=2, alpha=0.9)

        # TODAS as arestas (fundo cinza)
        all_edges = list(G.edges())
        weights = [G[u][v]['weight'] for u, v in G.edges()]
        max_weight = max(weights) if weights else 1

        nx.draw_networkx_edges(G, pos, edgelist=all_edges,
                               width=1, edge_color='gray', alpha=0.4,
                               style='dashed')

        matching_edges = list(matching_arestas)
        if matching_edges:
            matching_weights = [G[u][v]['weight'] for u, v in matching_edges]
            max_matching_weight = max(
                matching_weights) if matching_weights else 1

            for (u, v), weight in zip(matching_edges, matching_weights):
                normalized_weight = weight / max_matching_weight
                edge_color = plt.cm.Reds(normalized_weight)
                edge_width = 2 + normalized_weight * 4

                nx.draw_networkx_edges(G, pos, edgelist=[(u, v)],
                                       width=edge_width, edge_color=[
                                           edge_color],
                                       alpha=0.8)

        labels = {}
        font_sizes = {}
        for node in G.nodes():
            if len(node) > 20:
                parts = node.split()
                if len(parts) >= 2:
                    short_name = f"{parts[0]} {parts[-1]}"
                else:
                    short_name = node[:15] + "..."
            else:
                short_name = node

            labels[node] = short_name
            font_sizes[node] = 8 if len(short_name) > 15 else 9

        nx.draw_networkx_labels(G, pos, labels=labels, font_size=9,
                                font_weight='bold', font_family='DejaVu Sans')

        if matching_edges:
            sm = plt.cm.ScalarMappable(cmap=plt.cm.Reds,
                                       norm=plt.Normalize(0, max_matching_weight))
            sm.set_array([])
            cbar = plt.colorbar(
                sm, ax=plt.gca(), shrink=0.8, aspect=20, pad=0.02)
            cbar.set_label('Score do Matching', rotation=270, labelpad=15)

        plt.title(f"MATCHING - {team_atacante} (Atacantes) vs {team_defensor} (Defensores)\n"
                  f"Jogo ID: {MATCH_ID} | Arestas vermelhas: Matching de Peso Máximo",
                  fontsize=16, pad=20, fontweight='bold')

        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#FF6B35', edgecolor='black',
                  label=f'{team_atacante} (Atacantes)'),
            Patch(facecolor='#004E89', edgecolor='black',
                  label=f'{team_defensor} (Defensores)'),
            Patch(facecolor='red', alpha=0.7,
                  label='Arestas do Matching (Score)')
        ]
        plt.legend(handles=legend_elements, loc='upper center',
                   bbox_to_anchor=(0.5, -0.05), ncol=3, fontsize=12)

        plt.axis('off')
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        plt.show()

    def visualizar_matriz_heatmap(matriz, team_atacante, team_defensor, match_id):
        """Cria heatmap visual da matriz de adjacência"""
        if matriz is None or matriz.empty:
            return

        plt.figure(figsize=(12, 8))

        # Cria heatmap
        sns.heatmap(matriz, annot=True, cmap='YlOrRd', fmt='g',
                    cbar_kws={'label': 'Score de Vantagem'},
                    linewidths=0.5, linecolor='gray')

        plt.title(f'Matriz de Adjacência - {team_atacante} vs {team_defensor}\nJogo ID: {match_id}',
                  fontsize=14, fontweight='bold', pad=20)
        plt.xlabel(f'{team_defensor} (Defensores)', fontweight='bold')
        plt.ylabel(f'{team_atacante} (Atacantes)', fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)

        plt.tight_layout()
        plt.savefig(f'matriz_heatmap_{team_atacante}_{team_defensor}_{match_id}.png',
                    dpi=300, bbox_inches='tight')
        plt.show()

    # --- EXECUÇÃO PRINCIPAL ---
    print("\n--- ANÁLISE DE MATCHING COM VISUALIZAÇÃO APRIMORADA ---")

    # Matching TIME1 (Atacante) vs TIME2 (Defensor)
    print(f"\nAnalisando {time1} (Atacante) vs {time2} (Defensor)...")
    G_time1_time2_score = criar_grafo_score_vantagem(events, time1, time2)

    if G_time1_time2_score and G_time1_time2_score.number_of_edges() > 0:
        matching_time1_time2 = encontrar_matching_perfeito(G_time1_time2_score)

        matriz_1 = criar_matriz_adjacencia(
            G_time1_time2_score, time1, time2, MATCH_ID)

        visualizar_grafo_aprimorado(G_time1_time2_score, time1, time2,
                                    f'matching_aprimorado_{time1}_{time2}_{MATCH_ID}.png',
                                    matching_time1_time2)

        if matriz_1 is not None:
            visualizar_matriz_heatmap(matriz_1, time1, time2, MATCH_ID)

    # Matching TIME2 (Atacante) vs TIME1 (Defensor)
    print(f"\nAnalisando {time2} (Atacante) vs {time1} (Defensor)...")
    G_time2_time1_score = criar_grafo_score_vantagem(events, time2, time1)

    if G_time2_time1_score and G_time2_time1_score.number_of_edges() > 0:
        matching_time2_time1 = encontrar_matching_perfeito(G_time2_time1_score)

        matriz_2 = criar_matriz_adjacencia(
            G_time2_time1_score, time2, time1, MATCH_ID)

        visualizar_grafo_aprimorado(G_time2_time1_score, time2, time1,
                                    f'matching_aprimorado_{time2}_{time1}_{MATCH_ID}.png',
                                    matching_time2_time1)

        if matriz_2 is not None:
            visualizar_matriz_heatmap(matriz_2, time2, time1, MATCH_ID)

    print(f"\nANÁLISE DE MATCHING CONCLUÍDA!")
    print(f"Arquivos gerados:")
    if G_time1_time2_score and G_time1_time2_score.number_of_edges() > 0:
        print(f"  - matching_aprimorado_{time1}_{time2}_{MATCH_ID}.png")
        print(f"  - matriz_adjacencia_{time1}_{time2}_{MATCH_ID}.csv")
        print(f"  - matriz_heatmap_{time1}_{time2}_{MATCH_ID}.png")
    if G_time2_time1_score and G_time2_time1_score.number_of_edges() > 0:
        print(f"  - matching_aprimorado_{time2}_{time1}_{MATCH_ID}.png")
        print(f"  - matriz_adjacencia_{time2}_{time1}_{MATCH_ID}.csv")
        print(f"  - matriz_heatmap_{time2}_{time1}_{MATCH_ID}.png")

except Exception as e:
    print(f" ERRO: {e}")
