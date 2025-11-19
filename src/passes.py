from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os


def analisar_rede(match_id):
    """Executa a análise de rede de passes decisivos para o jogo informado."""

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

        def leads_to_shot(passe, chutes_time):
            """Retorna True se o passe leva a um chute dentro de 5s na mesma posse."""
            if chutes_time is None or chutes_time.empty:
                return False
            try:
                passe_s = (passe.get('minute', 0) or 0) * \
                    60 + (passe.get('second', 0) or 0)
            except (TypeError, KeyError):
                return False

            for _, chute in chutes_time.iterrows():
                try:
                    chute_s = (chute.get('minute', 0) or 0) * \
                        60 + (chute.get('second', 0) or 0)
                except (TypeError, KeyError):
                    continue
                delta = chute_s - passe_s
                if 0 < delta <= 5 and passe.get('possession') == chute.get('possession'):
                    return True
            return False

        def is_pass_in_penalty_area(passe):
            """Verifica se o passe foi feito dentro da grande área"""
            try:
                location = passe.get("location")
                if location and len(location) >= 2:
                    x, y = location[0], location[1]
                    return x > 102 and 18 < y < 62
            except (TypeError, IndexError, KeyError):
                return False
            return False

        def identificar_passes_decisivos(passes_df, team_name, all_events):
            decisivos = []
            chutes = all_events[(all_events["type"] == "Shot") & (
                all_events["team"] == team_name)]

            for _, passe in passes_df.iterrows():
                try:
                    condicoes = [
                        passe.get("pass_goal_assist") == True,
                        passe.get("pass_shot_assist") == True,
                        passe.get("pass_through_ball") == True,
                        passe.get("pass_cross") == True,
                        passe.get("play_pattern") == "Counter Attack",
                        is_pass_in_penalty_area(passe),
                        leads_to_shot(passe, chutes),
                    ]

                    if any(condicoes) and pd.notna(passe.get("pass_recipient")):
                        decisivos.append({
                            "player": passe["player"],
                            "pass_recipient": passe["pass_recipient"],
                            "team": team_name,
                        })
                except (KeyError, TypeError, IndexError):
                    continue

            return decisivos

        def criar_grafo_matriz(passes_decisivos):
            if not passes_decisivos:
                return None, pd.DataFrame()

            G = nx.DiGraph()
            df = pd.DataFrame(passes_decisivos)
            conexoes = df.groupby(
                ["player", "pass_recipient"]).size().reset_index(name="weight")

            for _, row in conexoes.iterrows():
                G.add_edge(row["player"], row["pass_recipient"],
                           weight=row["weight"])

            nodes = sorted(G.nodes())
            matriz = pd.DataFrame(0, index=nodes, columns=nodes)
            for u, v, data in G.edges(data=True):
                matriz.loc[u, v] = data["weight"]

            return G, matriz

        def visualizar_grafo(G, team_name, filename):
            if not G or G.number_of_edges() == 0:
                return

            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(G, k=2.0, iterations=50, seed=42)

            graus = dict(G.degree(weight="weight"))
            max_grau = max(graus.values()) if graus else 1
            cores = [graus[n] / max_grau for n in G.nodes()]

            nx.draw_networkx_nodes(
                G,
                pos,
                node_size=800,
                node_color=cores,
                cmap="Reds",
                edgecolors="black",
                linewidths=1.5,
                alpha=0.9,
            )
            nx.draw_networkx_edges(
                G, pos, edge_color="gray", alpha=0.5, arrows=True, arrowsize=15)
            nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")

            plt.title(f"REDE DE PASSES DECISIVOS - {team_name.upper()}\nJogo ID: {match_id}",
                      fontsize=13, fontweight="bold", pad=12)
            plt.axis("off")
            plt.tight_layout()
            plt.savefig(filename, dpi=300,
                        bbox_inches="tight", facecolor="white")
            plt.close()

        # Execução principal

        for time in [time1, time2]:
            print(f"\nAnalisando {time}...")
            passes = events[(events["type"] == "Pass") &
                            (events["team"] == time)].copy()
            decisivos = identificar_passes_decisivos(passes, time, events)

            if not decisivos:
                print("   Nenhum passe decisivo encontrado.")
                continue

            G, matriz = criar_grafo_matriz(decisivos)
            if G is None or G.number_of_nodes() == 0:
                print("   Grafo vazio.")
                continue

            graus = dict(G.degree(weight="weight"))
            top_jogador = max(graus.items(), key=lambda x: x[1])
            print(
                f"   Jogador mais conectado: {top_jogador[0]} ({top_jogador[1]} conexões)")

            matriz_path = os.path.join(
                data_path, f"matriz_passes_{time}_{match_id}.csv")
            matriz.to_csv(matriz_path, encoding="utf-8-sig")

            fig_file = os.path.join(
                fig_path, f"grafo_passes_{time}_{match_id}.png")
            visualizar_grafo(G, time, fig_file)

            print("   Arquivos salvos:")
            print(f"     - {os.path.relpath(matriz_path, base_dir)}")
            print(f"     - {os.path.relpath(fig_file, base_dir)}")

    except (OSError, ValueError, KeyError, IndexError, nx.NetworkXError) as e:
        print(f"[ERRO GERAL em Rede] {e.__class__.__name__}: {e}")
