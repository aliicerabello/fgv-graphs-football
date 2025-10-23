from statsbombpy import sb
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

def carregar_dados(match_id):
    """Carrega dados do jogo"""
    print(f"📥 Carregando jogo {match_id}...")
    events = sb.events(match_id=match_id)
    
    # Descobrir times automaticamente
    times = [t for t in events['team'].dropna().unique() if t]
    print(f"🆚 Times: {times[0]} vs {times[1]}")
    
    return events, times[0], times[1]

def analisar_passes_decisivos(events, time):
    """Encontra passes decisivos de um time - versão simplificada"""
    passes = events[(events['type'] == 'Pass') & (events['team'] == time)].copy()
    print(f"   🔄 {time}: {len(passes)} passes totais")
    
    passes_decisivos = []
    
    for _, passe in passes.iterrows():
        decisivo = False
        
        # Critérios simples
        if passe.get('pass_goal_assist') or passe.get('pass_shot_assist'):
            decisivo = True
        elif passe.get('pass_through_ball') or passe.get('pass_cross'):
            decisivo = True
        elif passe_muito_progressivo(passe):
            decisivo = True
            
        if decisivo and pd.notna(passe.get('pass_recipient')):
            passes_decisivos.append({
                'jogador': passe['player'],
                'recebedor': passe['pass_recipient'],
                'time': time
            })
    
    print(f"   🎯 {time}: {len(passes_decisivos)} passes decisivos")
    return passes_decisivos

def passe_muito_progressivo(passe):
    """Verifica se passe avança muito no campo"""
    try:
        if passe.get('location') and passe.get('pass_end_location'):
            inicio_x = passe['location'][0]
            fim_x = passe['pass_end_location'][0]
            return (fim_x - inicio_x) > 15  # Critério mais simples
    except:
        pass
    return False

def criar_grafo(passes_decisivos, nome_time):
    """Cria grafo a partir dos passes decisivos"""
    if not passes_decisivos:
        return None, pd.DataFrame()
    
    G = nx.DiGraph()
    
    # Contar conexões
    conexoes = {}
    for passe in passes_decisivos:
        chave = (passe['jogador'], passe['recebedor'])
        conexoes[chave] = conexoes.get(chave, 0) + 1
    
    # Adicionar arestas
    for (de, para), peso in conexoes.items():
        G.add_edge(de, para, weight=peso, time=nome_time)
    
    # Criar matriz
    jogadores = sorted(G.nodes())
    matriz = pd.DataFrame(0, index=jogadores, columns=jogadores)
    
    for de, para, dados in G.edges(data=True):
        matriz.loc[de, para] = dados['weight']
    
    return G, matriz

def analisar_grafo_simples(G, nome_time):
    """Faz análise do grafo SEM scipy"""
    if not G:
        return {}
    
    print(f"   📊 {nome_time}: {G.number_of_nodes()} jogadores, {G.number_of_edges()} conexões")
    
    # Métricas que não usam scipy
    metricas = {
        'grau': dict(G.degree(weight='weight')),
        'grau_entrada': dict(G.in_degree(weight='weight')),
        'grau_saida': dict(G.out_degree(weight='weight'))
    }
    
    # PageRank manual simples (versão simplificada)
    pagerank_simples = {}
    total_passes = sum(metricas['grau'].values())
    
    for jogador in G.nodes():
        # Simples: importância proporcional aos passes
        pagerank_simples[jogador] = metricas['grau'][jogador] / total_passes if total_passes > 0 else 0
    
    metricas['pagerank_simples'] = pagerank_simples
    
    # Top 3 jogadores
    top3 = sorted(pagerank_simples.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"   👑 Top influentes: {', '.join([f'{j} ({s:.3f})' for j, s in top3])}")
    
    return metricas

def visualizar_grafo_simples(G, nome_time, nome_arquivo):
    """Gera visualização do grafo SEM scipy"""
    if not G or G.number_of_nodes() == 0:
        return
    
    plt.figure(figsize=(12, 8))
    
    # Layout manual mais simples
    pos = {}
    nodes = list(G.nodes())
    
    # Distribuir nós em círculo
    for i, node in enumerate(nodes):
        angle = 2 * 3.14159 * i / len(nodes)
        pos[node] = (np.cos(angle), np.sin(angle))
    
    # Tamanho pelo grau total
    graus = dict(G.degree(weight='weight'))
    max_grau = max(graus.values()) if graus else 1
    tamanhos = [graus[j] / max_grau * 2000 + 200 for j in G.nodes()]
    
    # Cor pelo grau de entrada
    graus_entrada = dict(G.in_degree(weight='weight'))
    max_entrada = max(graus_entrada.values()) if graus_entrada else 1
    cores = [graus_entrada[j] / max_entrada for j in G.nodes()]
    
    nx.draw_networkx_nodes(G, pos, node_size=tamanhos, node_color=cores, 
                          cmap='Reds', alpha=0.8, edgecolors='black')
    
    # Arestas
    pesos = [G[u][v]['weight'] for u, v in G.edges()]
    max_peso = max(pesos) if pesos else 1
    larguras = [p / max_peso * 3 for p in pesos]
    
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True,
                          arrowsize=15, alpha=0.6, width=larguras)
    
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight='bold')
    
    plt.title(f"REDE DE PASSES DECISIVOS - {nome_time.upper()}")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"   📁 Gráfico salvo: {nome_arquivo}")

def analisar_jogo(match_id):
    """Função principal que analisa um jogo completo"""
    print(f"\n{'='*60}")
    print(f"🎯 ANALISANDO JOGO {match_id}")
    print(f"{'='*60}")
    
    try:
        # 1. Carregar dados
        events, time1, time2 = carregar_dados(match_id)
        
        # 2. Analisar cada time
        resultados = {}
        
        for time in [time1, time2]:
            print(f"\n🔵 Analisando {time}...")
            
            # Passes decisivos
            passes_decisivos = analisar_passes_decisivos(events, time)
            
            # Criar grafo
            G, matriz = criar_grafo(passes_decisivos, time)
            
            # Analisar (sem scipy)
            metricas = analisar_grafo_simples(G, time)
            
            # Visualizar (sem scipy)
            if G:
                visualizar_grafo_simples(G, time, f"grafo_{time}_{match_id}.png")
                matriz.to_csv(f"matriz_{time}_{match_id}.csv")
                print(f"   💾 Matriz salva: matriz_{time}_{match_id}.csv")
            
            resultados[time] = {
                'grafo': G,
                'metricas': metricas,
                'passes_decisivos': len(passes_decisivos)
            }
        
        # 3. Análise comparativa
        print(f"\n📈 COMPARAÇÃO: {time1} vs {time2}")
        print(f"   🎯 Passes decisivos: {time1} {resultados[time1]['passes_decisivos']} | {time2} {resultados[time2]['passes_decisivos']}")
        
        # Jogador mais influente de cada time
        for time in [time1, time2]:
            if resultados[time]['grafo']:
                pagerank = resultados[time]['metricas']['pagerank_simples']
                top_jogador = max(pagerank.items(), key=lambda x: x[1])
                print(f"   👑 {time}: {top_jogador[0]} ({top_jogador[1]:.3f})")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

# USO SIMPLES
if __name__ == "__main__":
    # Lista de jogos para analisar
    jogos = [
        3869685,  # Argentina vs França - Final Copa 2022
        8658,     # França vs Croácia - Final Copa 2018
    ]
    
    for jogo_id in jogos:
        sucesso = analisar_jogo(jogo_id)
        if sucesso:
            print(f"✅ Jogo {jogo_id} analisado com sucesso!\n")
        else:
            print(f"❌ Falha na análise do jogo {jogo_id}\n")
    
    print("🏁 ANÁLISES CONCLUÍDAS!")