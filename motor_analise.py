
import os
import re
import json
import base64
import requests

BASE_URL = "https://api.goal-api.com/v1"
API_KEY = os.getenv("GOAL_API_KEY")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
GITHUB_REF_NAME = os.getenv("GITHUB_REF_NAME", "main")

STATE_FILE = "alertas_enviados.json"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

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


def safe_int(value):
    try:
        if value is None:
            return None
        return int(value)
    except (ValueError, TypeError):
        return None


def get_minute(value):
    if not value:
        return None

    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


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


def load_sent_alerts():
    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{STATE_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        return set(), None

    response.raise_for_status()

    data = response.json()
    content = base64.b64decode(data["content"]).decode("utf-8")
    saved = json.loads(content)

    return set(saved.get("sent", [])), data["sha"]


def save_sent_alerts(sent, sha):
    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{STATE_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    content = json.dumps(
        {"sent": sorted(sent)},
        indent=2
    )

    encoded = base64.b64encode(
        content.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Atualizar registo de alertas do Cantos à Vista V2",
        "content": encoded,
        "branch": GITHUB_REF_NAME
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()["content"]["sha"]


def send_telegram(message):
    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise RuntimeError("Telegram não confirmou o envio.")


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

    status = fixture.get("matchStatus")
    period = fixture.get("matchPeriod")
    minute_text = fixture.get("matchMinute")
    minute = get_minute(minute_text)

    if status not in ["LIVE", "HALF_TIME"]:
        return None

    first_half_window = (
        period == "FIRST_HALF"
        and minute is not None
        and 35 <= minute <= 45
    ) or period == "HALF_TIME"

    second_half_window = (
        period == "SECOND_HALF"
        and minute is not None
        and 75 <= minute <= 90
    )

    if not first_half_window and not second_half_window:
        return None

    fixture_id = fixture.get("id")

    if not fixture_id:
        return None

    match = get_statistics(fixture_id)

    if match.get("hasStatistics") is False:
        return None

    full = match.get("fullTime", []) or []
    first = match.get("firstHalf", []) or []

    total = get_stat(full, "Corners")
    dangerous = get_stat(full, "Dangerous Attacks")
    shots = get_stat(full, "On Target")

    if total is None or dangerous is None or shots is None:
        return None

    total_corners = sum(total)
    dangerous_total = sum(dangerous)
    shots_total = sum(shots)

    if first_half_window:
        first_corners = total_corners
        second_corners = 0

        eligible = (
            total_corners >= FIRST_HALF["min_corners"]
            and dangerous_total >= FIRST_HALF["min_dangerous"]
            and shots_total >= FIRST_HALF["min_shots"]
        )

        market = "FIRST_HALF"
        market_name = "FINAL DA PRIMEIRA PARTE"

    else:
        first_data = get_stat(first, "Corners")

        if first_data is None:
            return None

        first_corners = sum(first_data)
        second_corners = total_corners - first_corners

        if second_corners < 0:
            return None

        eligible = (
            total_corners >= SECOND_HALF["min_total_corners"]
            and second_corners >= SECOND_HALF["min_half_corners"]
            and dangerous_total >= SECOND_HALF["min_dangerous"]
            and shots_total >= SECOND_HALF["min_shots"]
        )

        market = "SECOND_HALF"
        market_name = "FINAL DA SEGUNDA PARTE"

    if not eligible:
        return None

    home = fixture.get("homeTeamName", "Casa")
    away = fixture.get("awayTeamName", "Fora")
    score_home = fixture.get("homeScore", "?")
    score_away = fixture.get("awayScore", "?")

    message = (
        "⚽ <b>CANTOS À VISTA V2</b>\n\n"
        f"🏟️ <b>{home} - {away}</b>\n"
        f"📊 Resultado: {score_home} - {score_away}\n"
        f"⏱️ Minuto: {minute_text}\n"
        f"🎯 Mercado: <b>{market_name}</b>\n\n"
        f"🚩 Cantos totais: {total_corners}\n"
        f"🚩 Cantos na 1.ª parte: {first_corners}\n"
        f"🚩 Cantos na 2.ª parte: {second_corners}\n"
        f"⚡ Ataques perigosos: {dangerous_total}\n"
        f"🥅 Remates à baliza: {shots_total}\n\n"
        "Critérios Equilibrados cumpridos."
    )

    return {
        "key": f"{fixture_id}_{market}",
        "message": message
    }


def main():

    if not API_KEY:
        raise SystemExit("GOAL_API_KEY não encontrada.")

    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise SystemExit("Credenciais do Telegram em falta.")

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        raise SystemExit("Configuração GitHub em falta.")

    print("CANTOS À VISTA V2")
    print("A analisar jogos em direto...")

    sent, state_sha = load_sent_alerts()

    response = requests.get(
        f"{BASE_URL}/fixtures/live",
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    fixtures = response.json().get("data", [])

    print("Jogos em direto:", len(fixtures))

    alerts = 0

    for fixture in fixtures:
        try:
            result = analyze_fixture(fixture)

            if not result:
                continue

            if result["key"] in sent:
                continue

            send_telegram(result["message"])

            sent.add(result["key"])

            state_sha = save_sent_alerts(sent, state_sha)

            alerts += 1

            print("ALERTA ENVIADO:", result["key"])

        except Exception as error:
            print(
                "ERRO:",
                fixture.get("homeTeamName"),
                "-",
                fixture.get("awayTeamName"),
                error
            )

    print("=============================")
    print("ANÁLISE CONCLUÍDA")
    print("Alertas enviados:", alerts)


if __name__ == "__main__":
    main()
