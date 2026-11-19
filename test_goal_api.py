
import os
import json
import requests

BASE_URL = "https://api.goal-api.com/v1"
API_KEY = os.getenv("GOAL_API_KEY")

if not API_KEY:
    raise SystemExit("GOAL_API_KEY não encontrada")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

print("A testar estatísticas de cantos...")

response = requests.get(
    f"{BASE_URL}/fixtures/live",
    headers=HEADERS,
    timeout=30
)

print("Estado API:", response.status_code)
response.raise_for_status()

data = response.json()
fixtures = data.get("data", [])

print("Jogos encontrados:", len(fixtures))

for fixture in fixtures[:5]:

    fixture_id = fixture.get("id")

    print("\n================================")
    print("JOGO:", fixture.get("homeTeamName"), "-", fixture.get("awayTeamName"))
    print("MINUTO:", fixture.get("matchMinute"))
    print("ESTADO DO JOGO:")
    print(json.dumps({
        key: value for key, value in fixture.items()
        if "status" in key.lower() or "period" in key.lower()
        or "minute" in key.lower()
    }, indent=2, ensure_ascii=False))

    stats_response = requests.get(
        f"{BASE_URL}/fixtures/{fixture_id}/statistics",
        headers=HEADERS,
        timeout=30
    )

    print("Estado estatísticas:", stats_response.status_code)

    if stats_response.status_code != 200:
        continue

    stats_data = stats_response.json()
    match = stats_data.get("data", {}).get("match", {})

    for period in ["fullTime", "firstHalf", "secondHalf"]:

        stats = match.get(period, []) or []

        print(f"\nPERÍODO: {period}")

        corners = next(
            (item for item in stats
             if item.get("type") == "Corners"),
            None
        )

        if corners:
            print("CANTOS:", corners)
        else:
            print("Cantos não disponíveis")

    print("\nESTRUTURA DOS DADOS:")
    print(json.dumps(match, indent=2, ensure_ascii=False)[:5000])

print("\nDIAGNÓSTICO TERMINADO")
