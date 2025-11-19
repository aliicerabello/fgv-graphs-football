from find_id import selecionar_jogo_aleatorio
from passes import analisar_rede
from matching import analisar_matching


def main():
    print("SISTEMA INTEGRADO DE ANÁLISE STATSBOMB")

    usar_auto = input("Usar ID aleatório? (s/n): ").strip().lower()
    if usar_auto == 's':
        match_id = selecionar_jogo_aleatorio()
        if not match_id:
            print("Erro ao gerar ID aleatório.")
            return
        print(f"Usando jogo ID: {match_id}")
    else:
        match_id = int(input("Insira o ID do jogo no StatsBomb: "))

    print("\n--- Análise de Rede de Passes ---")
    analisar_rede(match_id)

    print("\n--- Análise de Matching ---")
    analisar_matching(match_id)


if __name__ == "__main__":
    main()
