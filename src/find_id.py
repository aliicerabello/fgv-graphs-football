import requests
import random


def buscar_50_ids_aleatorios():
    """Busca 50 IDs aleatórios sem precisar carregar todos os jogos"""

    url = "https://api.github.com/repos/statsbomb/open-data/contents/data/three-sixty"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            all_files = response.json()

            # Pega todos os nomes de arquivos JSON
            json_files = [file['name']
                          for file in all_files if file['name'].endswith('.json')]

            if not json_files:
                print("Nenhum jogo encontrado")
                return []

            # Escolhe 50 arquivos aleatórios
            files_aleatorios = random.sample(
                json_files, min(50, len(json_files)))

            # Converte para IDs
            ids_aleatorios = []
            for file in files_aleatorios:
                match_id = file.replace('.json', '')
                if match_id.isdigit():
                    ids_aleatorios.append(int(match_id))

            return ids_aleatorios
        else:
            print(f"Erro ao acessar GitHub: {response.status_code}")
            return []

    except Exception as e:
        print(f"Erro: {e}")
        return []


def selecionar_jogo_aleatorio():
    """Seleciona um jogo aleatório dos 50 aleatórios"""
    ids_aleatorios = buscar_50_ids_aleatorios()

    if ids_aleatorios:
        id_aleatorio = random.choice(ids_aleatorios)
        return id_aleatorio
    else:
        return None


# Executa
if __name__ == "__main__":
    id_jogo = selecionar_jogo_aleatorio()
    if id_jogo:
        print(f"ID para usar: {id_jogo}")
