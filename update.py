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
QUOTES = {"S&P 500": "^spx", "Nasdaq": "^ndq", "Dow Jones": "^dji", "Pétrole WTI": "cl.f", "Taux US 10 ans": "10usy.b"}

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

def summarize(h, q):
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not h: return None
    prompt = (
        "Tu es analyste financier. À partir UNIQUEMENT des titres et cours ci-dessous, écris en français simple, "
        "pour un débutant, un brief sur ce qui influence le S&P 500 (économie, taux, Fed, pétrole, géopolitique, résultats d'entreprises). "
        "N'invente aucun chiffre ni événement ; ne cite un agenda que s'il apparaît dans les titres. "
        'Réponds en JSON : {"titre": "une phrase", "en_bref": "2 phrases max", '
        '"causes": [{"titre": "...", "texte": "1-2 phrases"}] (3 max), "a_surveiller": ["..."] (3 max)}.\n\n'
        f"Date : {datetime.now(timezone.utc):%d/%m/%Y}\nCours : {json.dumps(q, ensure_ascii=False)}\n"
        "Titres :\n" + "\n".join(f"- [{x['source']}] {x['titre']}" for x in h[:60])
    )
    models = [os.environ["GEMINI_MODEL"]] if os.environ.get("GEMINI_MODEL") else ["gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-flash-latest"]
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode()
    for m in models:
        try:
            req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent", body,
                                         {"Content-Type": "application/json", "x-goog-api-key": key})
            r = json.load(urllib.request.urlopen(req, timeout=90))
            return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e: print("modèle ignoré :", m, e)
    return None

h, q = headlines(), quotes()
data = {"maj": datetime.now(timezone.utc).isoformat(), "cours": q, "resume": summarize(h, q), "titres": h[:40]}
json.dump(data, open("data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("OK :", len(h), "titres,", len(q), "cours, résumé :", bool(data["resume"]))
