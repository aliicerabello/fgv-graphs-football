import requests
import random


def buscar_50_ids_aleatorios():
    """Busca até 50 IDs aleatórios da API pública do StatsBomb."""
    url = "https://api.github.com/repos/statsbomb/open-data/contents/data/three-sixty"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Erro ao acessar GitHub: {response.status_code}")
            return []

        json_files = [f['name']
                      for f in response.json() if f['name'].endswith('.json')]
        if not json_files:
            print("Nenhum jogo encontrado")
            return []

        ids = [
            int(f.replace('.json', ''))
            for f in random.sample(json_files, min(50, len(json_files)))
            if f.replace('.json', '').isdigit()
        ]
        return ids

    except Exception as e:
        print(f"Erro: {e}")
        return []


def selecionar_jogo_aleatorio():
    """Seleciona um ID aleatório dentre os disponíveis."""
    ids = buscar_50_ids_aleatorios()
    return random.choice(ids) if ids else None


if __name__ == "__main__":
    id_jogo = selecionar_jogo_aleatorio()
    if id_jogo:
        print(f"ID para usar: {id_jogo}")
