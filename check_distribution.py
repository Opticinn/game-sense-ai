import json

GAMES_JSON = r"C:\Users\Rafli\.cache\kagglehub\datasets\fronkongames\steam-games-dataset\versions\31\games.json"

with open(GAMES_JSON, "r", encoding="utf-8") as f:
    data = json.load(f)

# Hitung total game >= 5000 reviews
count = sum(
    1 for game in data.values()
    if (game.get("positive", 0) + game.get("negative", 0)) >= 5000
)
print(f"Total game dengan review >= 5000: {count:,}")
print()

# Cek game populer
checks = ["dark souls", "elden ring", "skyrim", "minecraft", "witcher"]
for keyword in checks:
    for app_id, game in data.items():
        total = game.get("positive", 0) + game.get("negative", 0)
        name  = game.get("name", "")
        if keyword.lower() in name.lower() and total >= 5000:
            print(f"✅ {name} — {total:,} reviews")