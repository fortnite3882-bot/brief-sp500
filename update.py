import json, os, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

FEEDS = {
 "CNBC": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
 "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
 "MarketWatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
 "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
 "BBC Monde": "https://feeds.bbci.co.uk/news/world/rss.xml",
 "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
 "OilPrice": "https://oilprice.com/rss/main",
 "Fed": "https://www.federalreserve.gov/feeds/press_all.xml",
}
QUOTES = {"S&P 500": "^spx", "Nasdaq": "^ndq", "Dow Jones": "^dji", "Pétrole WTI": "cl.f", "Taux US 10 ans": "10usy.b", "VIX (peur)": "^vix"}

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (brief-bot)"})
    return urllib.request.urlopen(req, timeout=20).read()

def headlines():
    out, limit = [], datetime.now(timezone.utc) - timedelta(hours=36)
    for src, url in FEEDS.items():
        n = 0
        try:
            for it in ET.fromstring(get(url)).iter("item"):
                t = (it.findtext("title") or "").strip()
                try: dt = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc)
                except Exception: dt = None
                if t and (dt is None or dt > limit):
                    out.append({"source": src, "titre": t, "lien": (it.findtext("link") or "").strip()}); n += 1
                if n >= 8: break
        except Exception as e: print("flux ignoré :", src, e)
    return out

def quotes():
    res = []
    for nom, sym in QUOTES.items():
        try:
            row = get(f"https://stooq.com/q/l/?s={sym}&f=sd2t2ohlcv&h&e=csv").decode().splitlines()[1].split(",")
            o, c = float(row[3]), float(row[6])
            res.append({"nom": nom, "valeur": round(c, 2), "var": round((c / o - 1) * 100, 2)})
        except Exception as e: print("cours ignoré :", nom, e)
    return res

def calendar(day):
    try: ev = json.loads(get("https://nfs.faireconomy.media/ff_calendar_thisweek.json"))
    except Exception as e:
        print("calendrier ignoré :", e); return []
    out = []
    for e in ev:
        try: t = datetime.fromisoformat(e["date"]).astimezone(timezone.utc)
        except Exception: continue
        if e.get("country") == "USD" and e.get("impact") in ("High", "Medium") and t.date().isoformat() == day:
            out.append({"t": t.isoformat(), "titre": e["title"], "impact": 3 if e["impact"] == "High" else 2,
                        "prevu": e.get("forecast", ""), "precedent": e.get("previous", "")})
    return sorted(out, key=lambda x: x["t"])

def analyse(h, q, cal, teinte_hier):
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not h: return None
    prompt = (
        "Tu es un analyste financier pédagogue. À partir UNIQUEMENT des titres, cours et événements ci-dessous, rédige en français clair, "
        "pour un investisseur débutant mais curieux, une analyse approfondie de ce qui influence le S&P 500. N'invente aucun chiffre ni fait. "
        'Réponds en JSON : {"titre": "titre accrocheur d\'une phrase", "en_bref": "2 phrases", '
        '"analyse": [{"titre": "...", "texte": "3 à 4 phrases : cause, mécanisme, conséquence possible"}] (4 entrées : contexte global, taux et Fed, '
        'pétrole et géopolitique, entreprises et IA/résultats ; adapte selon les titres), '
        '"scenarios": {"haussier": "1-2 phrases", "baissier": "1-2 phrases"}, '
        '"sentiment": {"haussier": entier, "neutre": entier, "baissier": entier (somme 100), "explication": "1 phrase sur le ton général des titres et des analystes"}, '
        '"calendrier": [{"fr": "titre français", "pourquoi": "15 mots max"}] (une entrée par événement listé, même ordre ; [] si aucun), '
        f'"ambiance": {{"nom": "un mot évoquant l\'humeur du jour", "teinte": entier 0-359 choisi selon l\'humeur, différent de {teinte_hier}}}}}.\n\n'
        f"Date : {datetime.now(timezone.utc):%d/%m/%Y}\nCours : {json.dumps(q, ensure_ascii=False)}\n"
        "Événements américains du jour :\n" + ("\n".join(f"{i+1}. {c['titre']} (prévu {c['prevu']}, précédent {c['precedent']})" for i, c in enumerate(cal)) or "aucun") +
        "\nTitres :\n" + "\n".join(f"- [{x['source']}] {x['titre']}" for x in h[:60]))
    models = [os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-flash-latest"]
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode()
    for m in models:
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", body,
                                         {"Content-Type": "application/json", "x-goog-api-key": key})
            r = json.load(urllib.request.urlopen(req, timeout=120))
            return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e: print("modèle ignoré :", m, e)
    return None

now = datetime.now(timezone.utc); today = now.date().isoformat()
try: old = json.load(open("data.json", encoding="utf-8"))
except Exception: old = {}
prev, hier = old.get("aujourdhui"), old.get("hier")
if prev and prev.get("date") != today: hier = prev
h, q, cal = headlines(), quotes(), calendar(today)
r = analyse(h, q, cal, ((hier or {}).get("ambiance") or {}).get("teinte", "aucune"))
if not r and prev and prev.get("date") == today: r = prev.get("resume")
amb = (r or {}).get("ambiance") or {}
try: teinte = int(amb["teinte"]) % 360
except Exception: teinte = (now.timetuple().tm_yday * 47) % 360
for i, c in enumerate(cal):
    try: c["fr"], c["pourquoi"] = r["calendrier"][i]["fr"], r["calendrier"][i]["pourquoi"]
    except Exception: pass
entry = {"date": today, "maj": now.isoformat(), "cours": q, "resume": r, "calendrier": cal,
         "ambiance": {"nom": amb.get("nom", ""), "teinte": teinte}, "titres": h[:40]}
json.dump({"aujourdhui": entry, "hier": hier}, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OK :", len(h), "titres,", len(q), "cours,", len(cal), "événements, analyse :", bool(r))
