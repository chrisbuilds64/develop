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
    ALL_RULES_DE = json.load(f)["rules"]

with open("rules_en.json") as f:
    ALL_RULES_EN = json.load(f)["rules"]

MONTH_NAMES_DE = [
    "Jänner", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]

MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

DACH_REGIONS = {
    "wien": "Austria", "vienna": "Austria",
    "graz": "Austria", "salzburg": "Austria", "innsbruck": "Austria",
    "linz": "Austria", "klagenfurt": "Austria", "bregenz": "Austria",
    "zürich": "Switzerland", "zurich": "Switzerland",
    "bern": "Switzerland", "berne": "Switzerland",
    "basel": "Switzerland", "basle": "Switzerland",
    "genf": "Switzerland", "geneva": "Switzerland", "genève": "Switzerland",
    "luzern": "Switzerland", "lucerne": "Switzerland",
    "münchen": "Bavaria", "munich": "Bavaria",
    "nürnberg": "Bavaria", "nuremberg": "Bavaria",
    "augsburg": "Bavaria", "regensburg": "Bavaria",
    "würzburg": "Bavaria", "wurzburg": "Bavaria",
    "stuttgart": "Baden-Württemberg", "freiburg": "Baden-Württemberg",
    "heidelberg": "Baden-Württemberg", "karlsruhe": "Baden-Württemberg",
    "ulm": "Baden-Württemberg", "konstanz": "Baden-Württemberg", "constance": "Baden-Württemberg",
}

DACH_REGIONS_DE = {
    "wien": "Österreich", "vienna": "Österreich",
    "graz": "Österreich", "salzburg": "Österreich", "innsbruck": "Österreich",
    "linz": "Österreich", "klagenfurt": "Österreich", "bregenz": "Österreich",
    "zürich": "Schweiz", "zurich": "Schweiz",
    "bern": "Schweiz", "berne": "Schweiz",
    "basel": "Schweiz", "basle": "Schweiz",
    "genf": "Schweiz", "geneva": "Schweiz", "genève": "Schweiz",
    "luzern": "Schweiz", "lucerne": "Schweiz",
    "münchen": "Bayern", "munich": "Bayern",
    "nürnberg": "Bayern", "nuremberg": "Bayern",
    "augsburg": "Bayern", "regensburg": "Bayern",
    "würzburg": "Bayern", "wurzburg": "Bayern",
    "stuttgart": "Baden-Württemberg", "freiburg": "Baden-Württemberg",
    "heidelberg": "Baden-Württemberg", "karlsruhe": "Baden-Württemberg",
    "ulm": "Baden-Württemberg", "konstanz": "Baden-Württemberg", "constance": "Baden-Württemberg",
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
            headers={"User-Agent": "Feldorakel/1.0"},
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


def select_rules(month: int, weather: dict, lang: str = "de", n: int = 8) -> list[str]:
    rules = ALL_RULES_DE if lang == "de" else ALL_RULES_EN
    wtags = set(weather_tags(weather))
    month_rules = [r for r in rules if month in r.get("months", [])]
    general_rules = [r for r in rules if not r.get("months")]

    def score(r):
        return len(set(r.get("tags", [])) & wtags)

    month_rules.sort(key=score, reverse=True)
    pool = month_rules[:20] + general_rules
    return [r["text"] for r in random.sample(pool, min(n, len(pool)))]


def get_farmer_advice(location: str, weather: dict, rules: list[str], d: date, lang: str = "de") -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rules_text = "\n".join(f"• {r}" for r in rules)

    if lang == "en":
        region = DACH_REGIONS.get(location.lower(), "the Alpine region")
        month_name = MONTH_NAMES_EN[d.month - 1]
        prompt = f"""You are an ancient, wise farmer from {region} who has seen 80 harvests.
You speak with warmth, dry wit, and deep respect for traditional farming wisdom.
You have a healthy scepticism of modern bureaucracy, subsidy forms, and computer programmes.
Your language is direct, plain-spoken, occasionally gruff — but always warm.
You may throw in the odd word of local dialect.

Current conditions:
- Location: {location} ({region})
- Date: {month_name} {d.day}
- Weather: {weather['description']}, {weather['temp_c']}°C (feels like {weather['feels_like']}°C)
- Wind: {weather['wind_kmph']} km/h, Humidity: {weather['humidity']}%

Traditional farming proverbs for this season:
{rules_text}

Write a "Farmer's Daily Dispatch" for tomorrow (150–200 words):
- Quote 2–3 proverbs directly and explain them briefly
- Give practical (but slightly absurd) advice for tomorrow's weather
- Include one dry remark about bureaucracy, EU subsidy forms, or computer programmes
- Tone: warm, wise, slightly grumpy, with a twinkle
- Write in English
- Close with a memorable piece of wisdom in **bold**"""
    else:
        region = DACH_REGIONS_DE.get(location.lower(), "dem Alpenraum")
        month_name = MONTH_NAMES_DE[d.month - 1]
        prompt = f"""Du bist ein uralter, weiser Bauer aus {region}, der 80 Ernten gesehen hat.
Du sprichst mit Wärme, trockenem Humor und tiefem Respekt vor der bäuerlichen Weisheit.
Du hast eine gesunde Skepsis gegenüber modernem Bürokratismus, Formularen und Computerprogrammen.
Deine Sprache ist volkstümlich, direkt, manchmal leicht schnoddrig — aber immer herzlich.

Aktuelle Lage:
- Ort: {location} ({region})
- Datum: {d.day}. {month_name}
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
    lang: str = Form("de"),
):
    try:
        d = datetime.strptime(query_date, "%Y-%m-%d").date() if query_date else date.today()
        weather = get_weather(location)
        rules = select_rules(d.month, weather, lang)
        advice = get_farmer_advice(location, weather, rules, d, lang)
        return JSONResponse({
            "advice": advice,
            "weather": weather,
            "location": location,
            "date": d.strftime("%B %d, %Y"),
            "lang": lang,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
