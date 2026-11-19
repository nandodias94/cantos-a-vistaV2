
import os
import requests

BASE_URL = "https://api.goal-api.com/v1"
API_KEY = os.getenv("GOAL_API_KEY")

if not API_KEY:
    raise SystemExit("ERRO: GOAL_API_KEY não encontrada.")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

print("A testar ligação à GOAL API...")

response = requests.get(
    f"{BASE_URL}/fixtures/live",
    headers=HEADERS,
    timeout=30
)

print("Estado da API:", response.status_code)
response.raise_for_status()

result = response.json()

if not result.get("success"):
    raise SystemExit("A API não devolveu sucesso.")

fixtures = result.get("data", [])

print("Jogos em direto:", len(fixtures))

if not fixtures:
    print("Não existem jogos em direto neste momento.")
    raise SystemExit(0)

for fixture in fixtures[:5]:

    fixture_id = fixture.get("id")

    home = fixture.get("homeTeamName", "Casa")
    away = fixture.get("awayTeamName", "Fora")
    minute = fixture.get("matchMinute", "?")

    print("\n-------------------------")
    print(f"Jogo: {home} - {away}")
    print(f"Minuto: {minute}")
    print(
        f"Resultado: {fixture.get('homeTeamScore', 0)}"
        f" - {fixture.get('awayTeamScore', 0)}"
    )

    stats_response = requests.get(
        f"{BASE_URL}/fixtures/{fixture_id}/statistics",
        headers=HEADERS,
        timeout=30
    )

    print("Estado estatísticas:", stats_response.status_code)

    if stats_response.status_code != 200:
        print("Estatísticas indisponíveis.")
        continue

    stats_result = stats_response.json()
    match = stats_result.get("data", {}).get("match", {})

    for period in ["fullTime", "firstHalf", "secondHalf"]:

        period_stats = match.get(period, []) or []

        corners = next(
            (item for item in period_stats
             if item.get("type") == "Corners"),
            None
        )

        if corners:
            print(
                f"Cantos ({period}): "
                f"{corners.get('home', '?')} - "
                f"{corners.get('away', '?')}"
            )
        else:
            print(f"Cantos ({period}): indisponíveis")

print("\nTeste concluído.")
