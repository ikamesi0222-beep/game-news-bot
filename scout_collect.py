import requests
import json
import os
from datetime import datetime

os.makedirs("snapshots", exist_ok=True)

def get_new_releases():
    url = "https://store.steampowered.com/api/featuredcategories"
    res = requests.get(url)
    data = res.json()
    return data["new_releases"]["items"]

def get_review_summary(appid):
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all&purchase_type=all"
    res = requests.get(url)

    if res.status_code != 200:
        return None

    data = res.json()
    summary = data.get("query_summary", {})

    total = summary.get("total_reviews", 0)
    positive = summary.get("total_positive", 0)
    negative = summary.get("total_negative", 0)

    positive_rate = 0
    if total > 0:
        positive_rate = round((positive / total) * 100, 2)

    return {
        "total_reviews": total,
        "positive_reviews": positive,
        "negative_reviews": negative,
        "positive_rate": positive_rate,
        "steam_score": summary.get("review_score_desc", "Unknown")
    }

def get_current_players(appid):
    url = f"https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={appid}"
    res = requests.get(url)

    if res.status_code != 200:
        return 0

    data = res.json()
    return data.get("response", {}).get("player_count", 0)

games = get_new_releases()

results = []

for game in games[:50]:
    appid = game["id"]
    name = game["name"]

    review = get_review_summary(appid)
    players = get_current_players(appid)

    if review is None:
        continue

    results.append({
        "name": name,
        "appid": appid,
        "price": game.get("final_price"),
        "discount_percent": game.get("discount_percent"),
        "url": f"https://store.steampowered.com/app/{appid}",
        "current_players": players,
        "total_reviews": review["total_reviews"],
        "positive_rate": review["positive_rate"],
        "steam_score": review["steam_score"]
    })

today = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"snapshots/steam_new_releases_{today}.json"

with open(filename, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("保存完了:", filename)
print()

for game in results:
    print(game["name"])
    print("  好評率:", game["positive_rate"], "%")
    print("  レビュー数:", game["total_reviews"])
    print("  現在プレイヤー:", game["current_players"])
    print("  URL:", game["url"])
    print()
