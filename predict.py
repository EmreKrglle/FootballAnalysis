# -*- coding: utf-8 -*-
"""
FootballAnalysis - Tahmin Scripti (4 Sinifli)
Calistirma: python predict.py
"""

import requests
import torch
import os
from gnn_buildup_model import BuildupPlayGNN, sequence_to_graph, OUTCOME_TO_IDX, IDX_TO_OUTCOME, NUM_CLASSES

API_BASE   = "http://localhost:8000"
MODEL_PATH = "best_model.pt"

OUTCOME_SYMBOL = {
    "Yuksek Tehlike":  "[!!]",
    "Ilerleme":        "[->]",
    "Notr Kayip":      "[~] ",
    "Tehlikeli Kayip": "[X] ",
}

print("=" * 65)
print("  TAHMIN SISTEMI - 4 Sinifli Geriden Cikma Analizi")
print("=" * 65)

# ---------------------------------------------------------
#  1. MODEL YUKLE
# ---------------------------------------------------------

if not os.path.exists(MODEL_PATH):
    print(f"\n{MODEL_PATH} bulunamadi.")
    print("Once su komutu calistir: python train.py")
    exit()

checkpoint  = torch.load(MODEL_PATH, map_location="cpu")
num_classes = checkpoint.get("num_classes", NUM_CLASSES)
model       = BuildupPlayGNN(num_classes=num_classes)
model.load_state_dict(checkpoint["model_state"])
model.eval()
print(f"Model yuklendi: {MODEL_PATH}\n")

# ---------------------------------------------------------
#  2. MACLARI LISTELE
# ---------------------------------------------------------

try:
    matches = requests.get(f"{API_BASE}/matches", timeout=10).json()
except Exception as e:
    print(f"API baglantisi kurulamadi: {e}")
    exit()

print("Mevcut maclar:")
for i, m in enumerate(matches):
    print(f"  [{i}] {m['home_team']:<22} vs {m['away_team']:<22} "
          f"({m['home_score']}-{m['away_score']})  {m['match_date']}")

print()
try:
    idx   = int(input(f"Mac numarasi sec (0-{len(matches)-1}): "))
    match = matches[idx]
except (ValueError, IndexError):
    match = matches[0]
    print("Gecersiz giris, ilk mac secildi.")

match_id   = match["match_id"]
home_team  = match["home_team"]
away_team  = match["away_team"]
score_diff = match["home_score"] - match["away_score"]

print(f"\nSecilen mac : {home_team} vs {away_team}")
print(f"Skor        : {match['home_score']} - {match['away_score']}")

# ---------------------------------------------------------
#  3. TAKIM SEC
# ---------------------------------------------------------

print(f"\n  [0] {home_team}")
print(f"  [1] {away_team}")
try:
    team_idx = int(input("Takim (0 veya 1): "))
    team     = home_team if team_idx == 0 else away_team
except (ValueError, IndexError):
    team = home_team

team_score_diff = score_diff if team == home_team else -score_diff
print(f"\nTakim: {team}  |  Skor farki: {team_score_diff:+d}")

# ---------------------------------------------------------
#  4. SEKANSLAR
# ---------------------------------------------------------

print("\nSekanslar yukleniyor...")
try:
    data = requests.get(
        f"{API_BASE}/matches/{match_id}/sequences/{team}",
        timeout=10
    ).json()
except Exception as e:
    print(f"Hata: {e}")
    exit()

sequences = data.get("sequences", [])
print(f"{len(sequences)} sekans bulundu.\n")

if not sequences:
    print("Gosterilecek sekans yok.")
    exit()

# ---------------------------------------------------------
#  5. TAHMIN
# ---------------------------------------------------------

print("=" * 72)
print(f"  {team.upper()} -- SEKANS TAHMINLERI")
print("=" * 72)
print(f"{'Dk':>4}  {'Olay':>5}  {'Tahmin':<22}  {'Gercek':<22}  {'Guven':>6}  Sonuc")
print("-" * 72)

dogru  = 0
yanlis = 0
class_results = {k: {"dogru": 0, "yanlis": 0} for k in OUTCOME_TO_IDX}

for seq in sequences:
    try:
        x_dict, ei_dict, ea_dict, _ = sequence_to_graph(
            sequence_data=seq,
            match_context={
                "score_diff":     team_score_diff,
                "time_remaining": seq.get("end_minute", 45.0),
                "pressure_index": 0.5,
            },
        )

        with torch.no_grad():
            logits = model(x_dict, ei_dict, ea_dict, batch=None)
            probs  = torch.softmax(logits, dim=0)

        pred_idx = probs.argmax().item()
        tahmin   = IDX_TO_OUTCOME[pred_idx]
        guven    = probs[pred_idx].item()
        gercek   = seq.get("outcome", "?")
        isabet   = "OK" if tahmin == gercek else "--"
        sym_t    = OUTCOME_SYMBOL.get(tahmin, "    ")
        sym_g    = OUTCOME_SYMBOL.get(gercek, "    ")

        if tahmin == gercek:
            dogru += 1
            if gercek in class_results:
                class_results[gercek]["dogru"] += 1
        else:
            yanlis += 1
            if gercek in class_results:
                class_results[gercek]["yanlis"] += 1

        dk = f"{seq['start_minute']}'"
        print(f"{dk:>4}  {seq['event_count']:>5}  "
              f"{sym_t}{tahmin:<18}  {sym_g}{gercek:<18}  "
              f"{guven:>5.1%}  {isabet}")

    except Exception as e:
        print(f"  HATA: {e}")

# ---------------------------------------------------------
#  6. OZET
# ---------------------------------------------------------

toplam = dogru + yanlis
print("=" * 72)
print(f"\n  GENEL OZET")
print(f"  {'-'*40}")
print(f"  Toplam sekans  : {toplam}")
print(f"  Dogru tahmin   : {dogru}  ({dogru/toplam:.1%})")
print(f"  Yanlis tahmin  : {yanlis}  ({yanlis/toplam:.1%})")

print(f"\n  SINIF BAZLI DOGRULUK")
print(f"  {'-'*40}")
for outcome, sym in OUTCOME_SYMBOL.items():
    d      = class_results.get(outcome, {})
    d_sayi = d.get("dogru", 0)
    y_sayi = d.get("yanlis", 0)
    t      = d_sayi + y_sayi
    acc    = d_sayi / t if t > 0 else 0
    bar    = "#" * int(acc * 20)
    print(f"  {sym} {outcome:<20}: {d_sayi:>3}/{t:<4}  {acc:>5.1%}  {bar}")

print(f"\n  MAC GERCEK SEKANS DAGILIMI")
print(f"  {'-'*40}")
if "outcome_counts" in data:
    for outcome, count in data["outcome_counts"].items():
        sym = OUTCOME_SYMBOL.get(outcome, "    ")
        pct = count / max(len(sequences), 1)
        bar = "#" * int(pct * 30)
        print(f"  {sym} {outcome:<20}: {count:>4}  ({pct:.1%})  {bar}")

print()
if toplam > 0 and dogru / toplam >= 0.55:
    print("  Model iyi tahmin yapiyor -- egitim basarili.")
else:
    print("  Dogruluk dusuk -- daha fazla epoch ile yeniden egit.")