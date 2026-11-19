
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


def get_minute(value):
    if not value:
        return None

    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def safe_int(value):
    try:
        if value is None:
            return None
        return int(value)
    except (ValueError, TypeError):
        return None


def get_stat(stats, name):
    item = next(
        (x for x in stats if x.get("type") == name),
        None
    )

    if not item:
        return None

    home = safe_int(item.get("home"))
    away = safe_int(item.get("away"))

    if home is None or away is None:
        return None

    return home, away


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

    home = fixture.get("homeTeamName", "Casa")
    away = fixture.get("awayTeamName", "Fora")
    minute_text = fixture.get("matchMinute")
    period = fixture.get("matchPeriod")
    status = fixture.get("matchStatus")

    minute = get_minute(minute_text)

    print("\n--------------------------------")
    print(f"JOGO: {home} - {away}")
    print(f"MINUTO: {minute_text}")
    print(f"PERÍODO: {period}")
    print(f"ESTADO: {status}")

    if status not in ["LIVE", "HALF_TIME"]:
        print("IGNORADO: jogo não está LIVE")
        return False

    if period not in ["FIRST_HALF", "HALF_TIME", "SECOND_HALF"]:
        print("IGNORADO: período não elegível")
        return False

    first_half_window = (
        period == "FIRST_HALF"
        and minute is not None
        and 35 <= minute <= 45
    ) or period == "HALF_TIME"

    second_half_window = (
        period == "SECOND_HALF"
        and minute is not None
        and 75 <= minute <= 99
    )

    if not first_half_window and not second_half_window:
        print("IGNORADO: fora das janelas de análise")
        return False

    print("DENTRO DA JANELA: a consultar estatísticas...")

    match = get_statistics(fixture.get("id"))

    full = match.get("fullTime", []) or []
    first = match.get("firstHalf", []) or []

    if match.get("hasStatistics") is False:
        print("IGNORADO: API ainda não disponibilizou estatísticas")
        return False

    total = get_stat(full, "Corners")
    dangerous = get_stat(full, "Dangerous Attacks")
    shots = get_stat(full, "On Target")

    if total is None or dangerous is None or shots is None:
        print("IGNORADO: faltam estatísticas essenciais")
        return False

    total_home, total_away = total
    dangerous_home, dangerous_away = dangerous
    shots_home, shots_away = shots

    total_corners = total_home + total_away
    dangerous_total = dangerous_home + dangerous_away
    shots_total = shots_home + shots_away

    first_corners_data = get_stat(first, "Corners")

    if first_half_window:
        first_corners = total_corners
        second_corners = 0
    else:
        if first_corners_data is None:
            print("IGNORADO: cantos da primeira parte indisponíveis")
            return False

        first_corners = sum(first_corners_data)
        second_corners = total_corners - first_corners

        if second_corners < 0:
            print("IGNORADO: valores de cantos inconsistentes")
            return False

    print(f"CANTOS TOTAIS: {total_corners}")
    print(f"CANTOS 1.ª PARTE: {first_corners}")
    print(f"CANTOS 2.ª PARTE: {second_corners}")
    print(f"ATAQUES PERIGOSOS: {dangerous_total}")
    print(f"REMATES À BALIZA: {shots_total}")

    if first_half_window:
        eligible = (
            total_corners >= FIRST_HALF["min_corners"]
            and dangerous_total >= FIRST_HALF["min_dangerous"]
            and shots_total >= FIRST_HALF["min_shots"]
        )
        market = "PRIMEIRA PARTE"

    else:
        eligible = (
            total_corners >= SECOND_HALF["min_total_corners"]
            and second_corners >= SECOND_HALF["min_half_corners"]
            and dangerous_total >= SECOND_HALF["min_dangerous"]
            and shots_total >= SECOND_HALF["min_shots"]
        )
        market = "SEGUNDA PARTE"

    print(f"MERCADO: {market}")

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
            if analyze_fixture(fixture):
                eligible += 1

        except Exception as error:
            print(
                "ERRO AO ANALISAR:",
                fixture.get("homeTeamName"),
                "-",
                fixture.get("awayTeamName"),
                error
            )

    print("\n=============================")
    print("ANÁLISE CONCLUÍDA")
    print("Oportunidades elegíveis:", eligible)


if __name__ == "__main__":
    main()
