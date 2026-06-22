import requests
import json
import os
from datetime import datetime

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

os.makedirs("snapshots", exist_ok=True)

GENRE_KEYWORDS = {
    "FPS": 50,
    "First-Person Shooter": 50,
    "TPS": 50,
    "Third-Person Shooter": 50,
    "Shooter": 40,
    "Extraction": 40,
    "Tactical": 30,
}

SECONDARY_KEYWORDS = {
    "Co-op": 30,
    "Online Co-op": 30,
    "Cooperative": 30,
    "Multiplayer": 20,
    "Party": 25,
    "Horror": 20,
    "PvP": 20,
    "PvE": 15,
    "Survival": 15,
}

GROWTH_KEYWORDS = {
    "Progression": 20,
    "Loot": 18,
    "Skill Tree": 15,
    "Crafting": 15,
    "Base Building": 12,
    "RPG": 10,
    "Roguelite": 10,
    "Roguelike": 10,
}

def get_new_releases():
    url = "https://store.steampowered.com/api/featuredcategories"
    res = requests.get(url)
    data = res.json()
    return data["new_releases"]["items"]

def get_app_details(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&filters=basic"
    res = requests.get(url)

    if res.status_code != 200:
        return {}

    data = res.json()
    app_data = data.get(str(appid), {})

    if not app_data.get("success"):
        return {}

    return app_data.get("data", {})

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

def add_keyword_score(text, keywords, reasons, label, max_add=None):
    score = 0

    for keyword, point in keywords.items():
        if keyword.lower() in text:
            score += point
            reasons.append(f"{label}: {keyword} +{point}")

            if max_add is not None and score >= max_add:
                score = max_add
                break

    return score

def calculate_price_score(price):
    if price is None:
        return 0, "価格不明"

    yen = price / 100

    if yen == 0:
        return 20, "無料 +20"
    if yen <= 1000:
        return 18, "1000円以下 +18"
    if yen <= 2000:
        return 15, "2000円以下 +15"
    if yen <= 3000:
        return 10, "3000円以下 +10"
    if yen <= 5000:
        return 3, "5000円以下 +3"

    return -10, "5000円超 -10"

def calculate_scout_score(game):
    score = 0
    reasons = []

    text = (
        game["name"] + " " +
        game.get("short_description", "") + " " +
        " ".join(game.get("genres", [])) + " " +
        " ".join(game.get("categories", []))
    ).lower()

    genre_score = add_keyword_score(
        text,
        GENRE_KEYWORDS,
        reasons,
        "最優先ジャンル",
        max_add=70
    )
    score += genre_score

    secondary_score = add_keyword_score(
        text,
        SECONDARY_KEYWORDS,
        reasons,
        "次点ジャンル",
        max_add=40
    )
    score += secondary_score

    growth_score = add_keyword_score(
        text,
        GROWTH_KEYWORDS,
        reasons,
        "成長/積み上げ要素",
        max_add=30
    )
    score += growth_score

    price_score, price_reason = calculate_price_score(game.get("price"))
    score += price_score
    reasons.append(price_reason)

    if game["positive_rate"] >= 90:
        score += 10
        reasons.append("好評率90%以上 +10")
    elif game["positive_rate"] >= 80:
        score += 8
        reasons.append("好評率80%以上 +8")
    elif game["positive_rate"] >= 70:
        score += 5
        reasons.append("好評率70%以上 +5")

    if game["total_reviews"] >= 50:
        score += 8
        reasons.append("レビュー50件以上 +8")
    elif game["total_reviews"] >= 10:
        score += 5
        reasons.append("レビュー10件以上 +5")
    elif game["total_reviews"] >= 1:
        score += 3
        reasons.append("レビュー1件以上 +3")

    if game["current_players"] >= 500:
        score += 10
        reasons.append("現在プレイヤー500人以上 +10")
    elif game["current_players"] >= 100:
        score += 8
        reasons.append("現在プレイヤー100人以上 +8")
    elif game["current_players"] >= 10:
        score += 5
        reasons.append("現在プレイヤー10人以上 +5")
    elif game["current_players"] >= 1:
        score += 2
        reasons.append("現在プレイヤー1人以上 +2")

    return score, reasons

games = get_new_releases()
results = []

for game in games[:50]:
    appid = game["id"]
    name = game["name"]

    review = get_review_summary(appid)
    players = get_current_players(appid)
    details = get_app_details(appid)

    if review is None:
        continue

    genres = [g.get("description", "") for g in details.get("genres", [])]
    categories = [c.get("description", "") for c in details.get("categories", [])]
    short_description = details.get("short_description", "")

    item = {
        "name": name,
        "appid": appid,
        "price": game.get("final_price"),
        "discount_percent": game.get("discount_percent"),
        "url": f"https://store.steampowered.com/app/{appid}",
        "current_players": players,
        "total_reviews": review["total_reviews"],
        "positive_rate": review["positive_rate"],
        "steam_score": review["steam_score"],
        "genres": genres,
        "categories": categories,
        "short_description": short_description
    }

    scout_score, reasons = calculate_scout_score(item)

    item["scout_score"] = scout_score
    item["reasons"] = reasons

    results.append(item)

results.sort(key=lambda x: x["scout_score"], reverse=True)

today = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"snapshots/steam_scout_ranked_{today}.json"

with open(filename, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("保存完了:", filename)
print()

for i, game in enumerate(results, start=1):
    price_text = "不明"
    if game["price"] is not None:
        price_text = f"{game['price'] / 100:.0f}円"

    print(f"{i}位: {game['name']}")
    print("  スコア:", game["scout_score"])
    print("  価格:", price_text)
    print("  好評率:", game["positive_rate"], "%")
    print("  レビュー数:", game["total_reviews"])
    print("  現在プレイヤー:", game["current_players"])
    print("  ジャンル:", ", ".join(game["genres"]))
    print("  理由:", ", ".join(game["reasons"]))
    print("  URL:", game["url"])
    print()

if DISCORD_WEBHOOK_URL:
    message_header = f"Steam発掘候補ランキング\n保存ファイル: {filename}\n\n"

    messages = []
    current_message = message_header

    for i, game in enumerate(results[:30], start=1):
        price_text = "不明"
        if game["price"] is not None:
            price_text = f"{game['price'] / 100:.0f}円"

        line = (
            f"【{i}位】{game['name']}\n"
            f"スコア: {game['scout_score']} / 価格: {price_text}\n"
            f"好評率: {game['positive_rate']}% / "
            f"レビュー: {game['total_reviews']} / "
            f"現在プレイヤー: {game['current_players']}\n"
            f"ジャンル: {', '.join(game['genres'])}\n"
            f"理由: {', '.join(game['reasons'][:5])}\n"
            f"{game['url']}\n\n"
        )

        if len(current_message) + len(line) > 1800:
            messages.append(current_message)
            current_message = ""

        current_message += line

    if current_message:
        messages.append(current_message)

    for message in messages:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        print("Discord送信:", r.status_code)

    print("Discord処理終了")
else:
    print("Discord Webhook URLが設定されていません")
