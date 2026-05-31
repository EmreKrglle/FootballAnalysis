# -*- coding: utf-8 -*-
"""
FootballAnalysis - Model Egitim Scripti
Calistirma: python train.py
"""

import requests
import torch
import torch.nn as nn
import random
import time
import os
from torch.optim.lr_scheduler import CosineAnnealingLR
from gnn_buildup_model import BuildupPlayGNN, sequence_to_graph, OUTCOME_TO_IDX, IDX_TO_OUTCOME, NUM_CLASSES

API_BASE     = "http://localhost:8000"
EPOCHS       = 60
LR           = 1e-3
WEIGHT_DECAY = 1e-4
TRAIN_SPLIT  = 0.8
SAVE_PATH    = "best_model.pt"
SEED         = 42

torch.manual_seed(SEED)
random.seed(SEED)


# ---------------------------------------------------------
#  1. VERI TOPLAMA
# ---------------------------------------------------------

def collect_all_sequences():
    print("=" * 60)
    print("  VERI TOPLANIYOR")
    print("=" * 60)

    try:
        matches = requests.get(f"{API_BASE}/matches", timeout=10).json()
    except Exception as e:
        print(f"API baglantisi kurulamadi: {e}")
        print("uvicorn main:app --reload calisiyor mu?")
        exit()

    print(f"{len(matches)} mac bulundu.\n")

    all_samples  = []
    class_counts = {k: 0 for k in OUTCOME_TO_IDX}

    for match in matches:
        match_id   = match["match_id"]
        home_team  = match["home_team"]
        away_team  = match["away_team"]
        score_diff = match["home_score"] - match["away_score"]

        for team in [home_team, away_team]:
            try:
                resp = requests.get(
                    f"{API_BASE}/matches/{match_id}/sequences/{team}",
                    timeout=10
                ).json()
            except Exception:
                continue

            for seq in resp.get("sequences", []):
                outcome = seq.get("outcome", "")
                if outcome not in OUTCOME_TO_IDX:
                    continue
                try:
                    x_dict, ei_dict, ea_dict, label = sequence_to_graph(
                        sequence_data=seq,
                        match_context={
                            "score_diff":     score_diff if team == home_team else -score_diff,
                            "time_remaining": seq.get("end_minute", 45.0),
                            "pressure_index": 0.5,
                        },
                    )
                    all_samples.append((x_dict, ei_dict, ea_dict, int(label)))
                    class_counts[outcome] += 1
                except Exception:
                    continue

        print(f"  [{match_id}] {home_team} vs {away_team} -> {len(all_samples)} ornek")

    print(f"\nToplam {len(all_samples)} sekans toplandı.\n")
    print("Sinif Dagilimi:")
    for outcome, count in class_counts.items():
        pct = count / len(all_samples) * 100 if all_samples else 0
        bar = "#" * int(pct / 2)
        print(f"  {outcome:<20}: {count:>5}  ({pct:>5.1f}%)  {bar}")

    return all_samples


# ---------------------------------------------------------
#  2. VERI BOLME
# ---------------------------------------------------------

def split_data(samples, ratio=0.8):
    random.shuffle(samples)
    n = int(len(samples) * ratio)
    return samples[:n], samples[n:]


# ---------------------------------------------------------
#  3. SINIF DENGELEME
# ---------------------------------------------------------

def oversample_to_balance(samples):
    from collections import defaultdict
    by_class  = defaultdict(list)
    for s in samples:
        by_class[s[3]].append(s)

    max_count = max(len(v) for v in by_class.values())
    balanced  = []

    print("\nDengeleme sonrasi egitim seti:")
    for cls_idx, cls_samples in sorted(by_class.items()):
        outcome    = IDX_TO_OUTCOME[cls_idx]
        multiplier = max_count // len(cls_samples)
        remainder  = max_count  % len(cls_samples)
        oversampled = cls_samples * multiplier + random.sample(cls_samples, remainder)
        balanced.extend(oversampled)
        print(f"  {outcome:<20}: {len(cls_samples):>5} -> {len(oversampled):>5}")

    print(f"  {'TOPLAM':<20}: {len(samples):>5} -> {len(balanced):>5}")
    random.shuffle(balanced)
    return balanced


# ---------------------------------------------------------
#  4. EPOCH CALISTIRMA
# ---------------------------------------------------------

def run_epoch(model, samples, optimizer, criterion, training=True):
    model.train() if training else model.eval()

    total_loss    = 0.0
    correct       = 0
    class_correct = [0] * NUM_CLASSES
    class_total   = [0] * NUM_CLASSES

    ctx = torch.enable_grad() if training else torch.no_grad()

    with ctx:
        for x_dict, ei_dict, ea_dict, label in samples:
            label_t = torch.tensor([label], dtype=torch.long)        # (1,)
            logits  = model(x_dict, ei_dict, ea_dict, batch=None)     # (1, 4) veya (4,)


            if logits.dim() == 1:
                logits = logits.unsqueeze(0)                          # (4,) -> (1, 4)

            loss = criterion(logits, label_t)                         # (1,4) vs (1,)

            if training:
                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            total_loss += loss.item()
            pred = logits.squeeze(0).argmax().item()

            if pred == label:
                correct += 1
                class_correct[label] += 1
            class_total[label] += 1

    n        = len(samples)
    accuracy = correct / n

    return {
        "loss":          total_loss / n,
        "accuracy":      accuracy,
        "class_correct": class_correct,
        "class_total":   class_total,
    }


# ---------------------------------------------------------
#  5. ANA EGITIM DONGUSU
# ---------------------------------------------------------

def train():
    all_samples = collect_all_sequences()

    if len(all_samples) < 20:
        print("Yeterli veri yok (en az 20 sekans gerekli).")
        exit()

    train_data, val_data = split_data(all_samples, TRAIN_SPLIT)
    print(f"\nHam egitim seti : {len(train_data)} ornek")
    print(f"Validasyon seti : {len(val_data)} ornek")

    train_data = oversample_to_balance(train_data)

    model     = BuildupPlayGNN(num_classes=NUM_CLASSES)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-5)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    history      = []

    print("\n" + "=" * 60)
    print("  EGITIM BASLIYOR  (4 sinif)")
    print("=" * 60)
    print(f"{'Ep':>4}  {'T.Loss':>7}  {'T.Acc':>6}  {'V.Loss':>7}  {'V.Acc':>6}")
    print("-" * 60)

    start = time.time()

    for epoch in range(1, EPOCHS + 1):
        t = run_epoch(model, train_data, optimizer, criterion, training=True)
        v = run_epoch(model, val_data,   optimizer, criterion, training=False)
        scheduler.step()
        history.append({"epoch": epoch, "train": t, "val": v})

        flag = ""
        if v["accuracy"] > best_val_acc:
            best_val_acc = v["accuracy"]
            torch.save({
                "model_state": model.state_dict(),
                "num_classes": NUM_CLASSES,
                "outcome_map": OUTCOME_TO_IDX,
            }, SAVE_PATH)
            flag = "<-- kaydedildi"

        if epoch % 5 == 0 or epoch == 1:
            print(f"{epoch:>4}  {t['loss']:>7.4f}  {t['accuracy']:>5.1%}  "
                  f"{v['loss']:>7.4f}  {v['accuracy']:>5.1%}  {flag}")

    elapsed = time.time() - start
    print("-" * 60)
    print(f"\nEgitim tamamlandi! ({elapsed:.0f} saniye)")
    print(f"En iyi validasyon dogrulugu : {best_val_acc:.2%}")
    print(f"Model kaydedildi            : {SAVE_PATH}")

    print(f"\nSon epoch sinif bazli dogruluk:")
    for c in range(NUM_CLASSES):
        total   = v["class_total"][c]
        correct = v["class_correct"][c]
        acc     = correct / total if total > 0 else 0
        print(f"  {IDX_TO_OUTCOME[c]:<20}: {correct}/{total}  ({acc:.1%})")

    try:
        import matplotlib.pyplot as plt
        epochs = [h["epoch"] for h in history]
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        fig.suptitle("FootballAnalysis - GNN Egitim Sonuclari")

        axes[0].plot(epochs, [h["train"]["loss"] for h in history], label="Egitim")
        axes[0].plot(epochs, [h["val"]["loss"]   for h in history], label="Validasyon")
        axes[0].set_title("Kayip (Loss)")
        axes[0].set_xlabel("Epoch")
        axes[0].legend()
        axes[0].grid(True)

        axes[1].plot(epochs, [h["train"]["accuracy"] for h in history], label="Egitim")
        axes[1].plot(epochs, [h["val"]["accuracy"]   for h in history], label="Validasyon")
        axes[1].set_title("Dogruluk (Accuracy)")
        axes[1].set_xlabel("Epoch")
        axes[1].set_ylim(0, 1)
        axes[1].legend()
        axes[1].grid(True)

        plt.tight_layout()
        plt.savefig("training_results.png", dpi=120)
        print(f"Grafik kaydedildi: training_results.png")
        plt.close()
    except ImportError:
        print("Grafik icin: pip install matplotlib")

    return best_val_acc


def load_trained_model(path=SAVE_PATH):
    if not os.path.exists(path):
        print(f"{path} bulunamadi. Once train.py calistir.")
        return None
    checkpoint  = torch.load(path, map_location="cpu")
    num_classes = checkpoint.get("num_classes", NUM_CLASSES)
    model       = BuildupPlayGNN(num_classes=num_classes)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    print(f"Egitilmis model yuklendi: {path}")
    return model


if __name__ == "__main__":
    train()