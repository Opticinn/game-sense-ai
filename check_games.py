import json

GAMES_JSON = r"C:\Users\Rafli\.cache\kagglehub\datasets\fronkongames\steam-games-dataset\versions\31\games.json"

with open(GAMES_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

keywords = ["dark souls", "elden ring", "sekiro", "hollow knight", "skyrim"]

for keyword in keywords:
    print(f"\n=== '{keyword}' ===")
    for app_id, game in data.items():
        name  = game.get("name", "")
        if keyword.lower() in name.lower():
            total = game.get("positive", 0) + game.get("negative", 0)
            print(f"  {app_id}: {name} — {total:,} reviews")