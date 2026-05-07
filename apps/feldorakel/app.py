import os
import json
import random
from datetime import date, datetime
from typing import Optional

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import anthropic

app = FastAPI(title="Feldorakel")
app.mount("/static", StaticFiles(directory="templates"), name="static")
templates = Jinja2Templates(directory="templates")

with open("rules.json") as f:
    ALL_RULES = json.load(f)["rules"]

MONTH_NAMES = [
    "Jänner", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

DACH_REGIONS = {
    "wien": "Österreich", "vienna": "Österreich",
    "graz": "Österreich", "salzburg": "Österreich", "innsbruck": "Österreich",
    "linz": "Österreich", "klagenfurt": "Österreich", "bregenz": "Österreich",
    "zürich": "Schweiz", "zurich": "Schweiz", "bern": "Schweiz",
    "basel": "Schweiz", "genf": "Schweiz", "luzern": "Schweiz",
    "münchen": "Bayern", "munich": "Bayern", "nürnberg": "Bayern",
    "augsburg": "Bayern", "regensburg": "Bayern", "würzburg": "Bayern",
    "stuttgart": "Baden-Württemberg", "freiburg": "Baden-Württemberg",
    "heidelberg": "Baden-Württemberg", "karlsruhe": "Baden-Württemberg",
    "ulm": "Baden-Württemberg", "konstanz": "Baden-Württemberg",
}

WEATHER_TAG_MAP = {
    "rain": "regen", "drizzle": "regen", "shower": "regen",
    "snow": "schnee", "sleet": "schnee",
    "clear": "sonne", "sunny": "sonne",
    "cloud": "nebel", "fog": "nebel", "mist": "nebel", "overcast": "nebel",
    "storm": "sturm", "thunder": "gewitter",
    "wind": "wind",
}


def get_weather(location: str) -> dict:
    try:
        resp = httpx.get(
            f"https://wttr.in/{location}?format=j1",
            timeout=10,
            headers={"User-Agent": "Plowcast/1.0"},
        )
        data = resp.json()
        current = data["current_condition"][0]
        return {
            "temp_c": int(current["temp_C"]),
            "description": current["weatherDesc"][0]["value"],
            "wind_kmph": int(current["windspeedKmph"]),
            "humidity": int(current["humidity"]),
            "feels_like": int(current["FeelsLikeC"]),
        }
    except Exception:
        return {
            "temp_c": 12,
            "description": "partly cloudy",
            "wind_kmph": 15,
            "humidity": 65,
            "feels_like": 10,
        }


def weather_tags(weather: dict) -> list[str]:
    desc = weather["description"].lower()
    tags = [v for k, v in WEATHER_TAG_MAP.items() if k in desc]
    if weather["temp_c"] >= 25:
        tags.append("hitze")
    elif weather["temp_c"] <= 2:
        tags.append("kälte")
    elif weather["temp_c"] <= 0:
        tags.append("frost")
    return tags


def select_rules(month: int, weather: dict, n: int = 8) -> list[str]:
    wtags = set(weather_tags(weather))
    month_rules = [r for r in ALL_RULES if month in r.get("months", [])]
    general_rules = [r for r in ALL_RULES if not r.get("months")]

    # Score by tag match
    def score(r):
        return len(set(r.get("tags", [])) & wtags)

    month_rules.sort(key=score, reverse=True)
    pool = month_rules[:20] + general_rules
    return [r["text"] for r in random.sample(pool, min(n, len(pool)))]


def get_farmer_advice(location: str, weather: dict, rules: list[str], d: date) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rules_text = "\n".join(f"• {r}" for r in rules)
    region = DACH_REGIONS.get(location.lower(), "dem Alpenraum")

    prompt = f"""Du bist ein uralter, weiser Bauer aus {region}, der 80 Ernten gesehen hat.
Du sprichst mit Wärme, trockenem Humor und tiefem Respekt vor der bäuerlichen Weisheit.
Du hast eine gesunde Skepsis gegenüber modernem Bürokratismus, Formularen und Computerprogrammen.
Deine Sprache ist volkstümlich, direkt, manchmal leicht schnoddrig — aber immer herzlich.

Aktuelle Lage:
- Ort: {location} ({region})
- Datum: {d.strftime('%d.')} {MONTH_NAMES[d.month - 1]}
- Wetter gerade: {weather['description']}, {weather['temp_c']}°C (gefühlt {weather['feels_like']}°C)
- Wind: {weather['wind_kmph']} km/h, Luftfeuchtigkeit: {weather['humidity']}%

Bauernregeln für diese Jahreszeit:
{rules_text}

Schreibe einen "Bäuerlichen Tagesbefehl" für morgen (150–200 Wörter):
- Zitiere 2–3 Bauernregeln direkt (auf Deutsch) und erkläre sie kurz
- Gib praktische (aber leicht absurde) Ratschläge für den nächsten Tag passend zum Wetter
- Einen trockenen Kommentar über Bürokratie, EU-Förderanträge oder Computerprogramme einbauen
- Ton: warm, weise, leicht grantig, mit Augenzwinkern
- Schreibe auf Deutsch
- Schließe mit einem unvergesslichen Weisheitssatz in **Fettschrift** ab"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/forecast")
async def forecast(
    location: str = Form(...),
    query_date: Optional[str] = Form(None),
):
    try:
        d = datetime.strptime(query_date, "%Y-%m-%d").date() if query_date else date.today()
        weather = get_weather(location)
        rules = select_rules(d.month, weather)
        advice = get_farmer_advice(location, weather, rules, d)
        return JSONResponse({
            "advice": advice,
            "weather": weather,
            "location": location,
            "date": d.strftime("%B %d, %Y"),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
