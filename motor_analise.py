
import os
import re
import requests

BASE_URL = "https://api.goal-api.com/v1"
API_KEY = os.getenv("GOAL_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

# CRITÉRIOS EQUILIBRADOS
FIRST_HALF = {
    "min_corners": 5,
    "min_dangerous": 20,
    "min_shots": 1,
}

SECOND_HALF = {
    "min_total_corners": 7,
    "min_half_corners": 2,
    "min_dangerous": 50,
    "min_shots": 3,
}


def get_stat(stats, name):
    item = next(
        (x for x in stats if x.get("type") == name),
        None
    )

    if not item:
        return 0, 0

    return (
        int(item.get("home") or 0),
        int(item.get("away") or 0)
    )


def get_minute(value):
    if not value:
        return None

    match = re.search(r"\d+", str(value))

    return int(match.group()) if match else None


def get_statistics(fixture_id):
    response = requests.get(
        f"{BASE_URL}/fixtures/{fixture_id}/statistics",
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    return result.get("data", {}).get("match", {})


def analyze_fixture(fixture):

    fixture_id = fixture.get("id")
    status = fixture.get("matchStatus")
    period = fixture.get("matchPeriod")
    minute_text = fixture.get("matchMinute")
    minute = get_minute(minute_text)

    # Excluir jogos que não estejam em tempo regulamentar
    if status != "LIVE":
        return None

    if period not in ["FIRST_HALF", "HALF_TIME", "SECOND_HALF"]:
        return None

    # Identificar a janela da primeira parte
    first_half_window = (
        period == "FIRST_HALF" and
        minute is not None and
        35 <= minute <= 45
    ) or period == "HALF_TIME"

    # Identificar a janela da segunda parte
    second_half_window = (
        period == "SECOND_HALF" and
        minute is not None and
        75 <= minute <= 120
    )

    if not first_half_window and not second_half_window:
        return None

    match = get_statistics(fixture_id)

    full = match.get("fullTime", []) or []
    first = match.get("firstHalf", []) or []

    total_home, total_away = get_stat(full, "Corners")
    first_home, first_away = get_stat(first, "Corners")

    dangerous_home, dangerous_away = get_stat(
        full, "Dangerous Attacks"
    )

    shots_home, shots_away = get_stat(
        full, "On Target"
    )

    total_corners = total_home + total_away
    first_corners = first_home + first_away

    second_corners = max(
        0,
        total_corners - first_corners
    )

    dangerous = dangerous_home + dangerous_away
    shots = shots_home + shots_away

    home = fixture.get("homeTeamName", "Casa")
    away = fixture.get("awayTeamName", "Fora")

    if first_half_window:

        criteria = FIRST_HALF

        eligible = (
            total_corners >= criteria["min_corners"]
            and dangerous >= criteria["min_dangerous"]
            and shots >= criteria["min_shots"]
        )

        market = "PRIMEIRA PARTE"

    else:

        criteria = SECOND_HALF

        eligible = (
            total_corners >= criteria["min_total_corners"]
            and second_corners >= criteria["min_half_corners"]
            and dangerous >= criteria["min_dangerous"]
            and shots >= criteria["min_shots"]
        )

        market = "SEGUNDA PARTE"

    print("\n-----------------------------")
    print(f"JOGO: {home} - {away}")
    print(f"MINUTO: {minute_text}")
    print(f"PERÍODO: {market}")
    print(f"CANTOS TOTAIS: {total_corners}")
    print(f"CANTOS 1.ª PARTE: {first_corners}")
    print(f"CANTOS 2.ª PARTE: {second_corners}")
    print(f"ATAQUES PERIGOSOS: {dangerous}")
    print(f"REMATES À BALIZA: {shots}")

    if eligible:
        print("RESULTADO: OPORTUNIDADE ELEGÍVEL")
    else:
        print("RESULTADO: NÃO ELEGÍVEL")

    return eligible


def main():

    if not API_KEY:
        raise SystemExit("GOAL_API_KEY não encontrada.")

    print("CANTOS À VISTA V2")
    print("A analisar jogos em direto...")

    response = requests.get(
        f"{BASE_URL}/fixtures/live",
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    fixtures = response.json().get("data", [])

    print(f"Jogos em direto: {len(fixtures)}")

    eligible = 0

    for fixture in fixtures:

        try:
            result = analyze_fixture(fixture)

            if result:
                eligible += 1

        except Exception as error:
            print(
                "Erro ao analisar jogo:",
                fixture.get("id"),
                error
            )

    print("\n=============================")
    print("ANÁLISE CONCLUÍDA")
    print("Oportunidades elegíveis:", eligible)


if __name__ == "__main__":
    main()
