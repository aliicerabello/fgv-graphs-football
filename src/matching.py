import os
from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def analisar_matching(match_id):
    """Executa a análise de matching tático bipartido para o jogo informado."""

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    fig_dir = os.path.join(base_dir, "figures")

    try:
        events = sb.events(match_id=match_id)
        times = [t for t in events['team'].dropna().unique() if t]
        time1, time2 = times[0], times[1]
        print(f" {time1} vs {time2}")

        nome_jogo = f"{time1}_vs_{time2}".replace(" ", "_")
        data_path = os.path.join(data_dir, nome_jogo)
        fig_path = os.path.join(fig_dir, nome_jogo)
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(fig_path, exist_ok=True)

        # Funções auxiliares
        def encontrar_driblador_desarmado(events, tackle_index, team_atacante):
            try:
                prev_event = events[events['index']
                                    == tackle_index - 1].iloc[0]
                if prev_event['type'] == 'Dribble' and prev_event['team'] == team_atacante:
                    if prev_event.get('dribble_outcome') != 'Complete':
                        return prev_event['player']
            except (IndexError, KeyError, TypeError):
                pass
            return None

        def criar_grafo_score_vantagem(events, team_atacante, team_defensor):
            G = nx.Graph()
            confrontos = []

            defensive_actions = events[
                (events['team'] == team_defensor) &
                (events['type'].isin(
                    ['Duel', 'Block', 'Interception', 'Ball Recovery', 'Foul Won']))
            ].copy()

            for _, def_event in defensive_actions.iterrows():
                defensor = def_event['player']
                atacante = None
                score = 0

                try:
                    if def_event['type'] == 'Duel' and def_event.get('duel_type') == 'Tackle':
                        atacante_driblador = encontrar_driblador_desarmado(
                            events, def_event['index'], team_atacante)
                        if atacante_driblador and def_event.get('duel_outcome') == 'Won':
                            atacante = atacante_driblador
                            score = 3

                    elif def_event['type'] == 'Block':
                        shot_event = events[
                            (events['type'] == 'Shot') &
                            (events['index'] == def_event['index'] - 1) &
                            (events['team'] == team_atacante)
                        ].iloc[0]
                        if shot_event.get('shot_outcome') == 'Blocked':
                            atacante = shot_event['player']
                            score = 2

                    elif def_event['type'] in ['Interception', 'Ball Recovery']:
                        prev_event = events[events['index']
                                            == def_event['index'] - 1].iloc[0]
                        if prev_event['team'] == team_atacante and prev_event['type'] == 'Pass' and \
                                prev_event.get('pass_outcome') in ['Incomplete', 'Out']:
                            atacante = prev_event['player']
                            score = 1

                    elif def_event['type'] == 'Foul Won':
                        related_foul = events[events['related_events'].apply(
                            lambda x: def_event['id'] in x if isinstance(
                                x, list) else False
                        )].iloc[0]
                        if related_foul['team'] == team_atacante:
                            atacante = related_foul['player']
                            score = 1
                except (IndexError, KeyError, TypeError):
                    pass

                if atacante and defensor and score > 0:
                    confrontos.append((atacante, defensor, score))

            if not confrontos:
                print(
                    f"Nenhum confronto entre {team_atacante} e {team_defensor}")
                return G

            df = pd.DataFrame(confrontos, columns=[
                              'atacante', 'defensor', 'score'])
            conexao = df.groupby(['atacante', 'defensor'])[
                'score'].sum().reset_index(name='weight')

            a_nodes = set(conexao['atacante'])
            b_nodes = set(conexao['defensor'])
            G.add_nodes_from(a_nodes, bipartite=0)
            G.add_nodes_from(b_nodes, bipartite=1)
            for _, row in conexao.iterrows():
                G.add_edge(row['atacante'], row['defensor'],
                           weight=row['weight'])
            return G

        def encontrar_matching(G):
            if not G or G.number_of_edges() == 0:
                return set()
            try:
                return nx.max_weight_matching(G, maxcardinality=False)
            except nx.NetworkXError as e:
                print(f"Erro no matching: {e}")
                return set()

        def criar_matriz(G, team_atacante, team_defensor):
            if G.number_of_edges() == 0:
                return
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
            path = os.path.join(
                data_path, f"matriz_matching_{team_atacante}_{team_defensor}.csv")
            matriz.to_csv(path, encoding='utf-8-sig')

        def visualizar_grafo(G, matching_edges, team_atacante, team_defensor, filename):
            if G.number_of_edges() == 0:
                return

            plt.figure(figsize=(20, 12))
            nodes_a = {n for n, d in G.nodes(
                data=True) if d.get('bipartite') == 0}
            nodes_b = {n for n, d in G.nodes(
                data=True) if d.get('bipartite') == 1}
            pos = nx.bipartite_layout(G, nodes_a, scale=2.0, aspect_ratio=1.2)
            for node, (x, y) in pos.items():
                pos[node] = (x - 1.5, y) if node in nodes_a else (x + 1.5, y)

            nx.draw_networkx_nodes(
                G, pos, nodelist=nodes_a, node_color="#FF6B35", node_size=1200, edgecolors='black')
            nx.draw_networkx_nodes(
                G, pos, nodelist=nodes_b, node_color="#004E89", node_size=1200, edgecolors='black')
            nx.draw_networkx_edges(
                G, pos, width=1, edge_color='gray', alpha=0.4, style='dashed')

            if matching_edges:
                weights = [G[u][v]['weight'] for u, v in matching_edges]
                max_w = max(weights) if weights else 1
                for (u, v), w in zip(matching_edges, weights):
                    color = plt.cm.Reds(w / max_w)
                    nx.draw_networkx_edges(
                        G, pos, edgelist=[(u, v)], width=2 + 4 * (w / max_w), edge_color=[color])

            nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold')
            legend_elements = [
                Patch(facecolor='#FF6B35', edgecolor='black',
                      label=f'{team_atacante} (Atacantes)'),
                Patch(facecolor='#004E89', edgecolor='black',
                      label=f'{team_defensor} (Defensores)'),
                Patch(facecolor='red', alpha=0.7, label='Arestas do Matching')
            ]
            plt.legend(handles=legend_elements, loc='upper center',
                       bbox_to_anchor=(0.5, -0.05), ncol=3)
            plt.title(
                f"Matching Tático: {team_atacante} (Ataque) vs {team_defensor} (Defesa)\nID: {match_id}")
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(filename, dpi=300,
                        bbox_inches='tight', facecolor='white')
            plt.close()

        # Execução
        for ataque, defesa in [(time1, time2), (time2, time1)]:
            print(f"\nAnalisando {ataque} (Atacante) vs {defesa} (Defensor)")
            G = criar_grafo_score_vantagem(events, ataque, defesa)
            if G.number_of_edges() > 0:
                criar_matriz(G, ataque, defesa)
                matching = encontrar_matching(G)
                fig_file = os.path.join(
                    fig_path, f"grafo_matching_{ataque}_{defesa}_{match_id}.png")
                visualizar_grafo(G, matching, ataque, defesa, fig_file)
                print(f"  Grafo salvo em {fig_file}")

    except Exception as e:
        print(f"[ERRO em Matching] {e.__class__.__name__}: {e}")
