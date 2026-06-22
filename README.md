# ⚽ FootballAnalysis

**Graph Neural Network tabanlı futbol taktik analiz platformu.**  
StatsBomb açık verisi üzerinde 22 oyunculu heterojen graf mimarisi kullanarak geriden oyun kurma (build-up play) başarısını tahmin eder ve rakip oyuncu analizi yapar.

---

## 🎯 Ne Yapıyor?

### Build-Up Analizi
Sahada 11 kendi + 11 rakip oyuncusunu interaktif olarak hareket ettir. Model her harekette anlık tahmin üretir:

| Sınıf | Anlam |
|-------|-------|
| 🔴 Yüksek Tehlike | Şut veya ceza sahasına giriş bekleniyor |
| 🟡 İlerleme | Rakip yarısına geçiş, faul kazanma |
| 🔵 Nötr Kayıp | Rakip yarısında zararsız top kaybı |
| ⚫ Tehlikeli Kayıp | Kendi yarısında tehlikeli top kaybı |

### Rakip Oyuncu Analizi *(geliştirme aşamasında)*
Belirli bir rakip oyuncuyu seç, kendi baskı şemanı sahaya çiz. Model o oyuncunun bu baskı altındaki pas başarısını ve hedef dağılımını tahmin eder.

---

## 🧠 Model Mimarisi

```
11 Kendi Oyuncu ──┐
                   ├──► Heterojen GNN ──► 4 Sınıf Tahmini
11 Rakip Oyuncu ──┤         ▲
                   │         │
1 Master Node  ────┘    Global Bağlam
                       (Skor, Dakika,
                        Rakip Baskı)
```

### Graf Yapısı

```
Düğüm tipleri:
  own    → 11 kendi oyuncu  (7 özellik: x, y, rol×3, pas başarısı, aktör)
  opp    → 11 rakip oyuncu  (5 özellik: x, y, kaleci, saha oyuncusu, baskı yarıçapı)
  master → 1 global düğüm   (4 özellik: skor farkı, kalan süre, rakip baskı, alan hakimiyeti)

Kenar tipleri:
  own  → own     pas kanalı (mesafe, zorluk, baskı bayrağı)
  own  → opp     baskı altında mı?
  opp  → own     rakip baskı uyguluyor
  own  → master  upward aggregation
  opp  → master  upward aggregation
  master → own   global bağlam enjeksiyonu
  master → opp   global bağlam enjeksiyonu
```

### Mesaj İletim Formülü

$$h_v^{(l+1)} = \sigma \left( \text{gate} \odot \sum_{u \in \mathcal{N}(v)} \alpha_{vu} W h_u^{(l)} + (1 - \text{gate}) \odot W_{\text{master}} h_{\text{master}}^{(l)} \right)$$

### Eğitim Sonuçları

```
Veri kaynağı  : StatsBomb Euro 2024 (51 maç, 2.7M freeze-frame)
Eğitim örneği : 60.000 sekans bazlı freeze-frame
Etiketleme    : Her freeze-frame, ait olduğu sekansın sonucuyla etiketlendi
Validasyon    : %80 eğitim / %20 validasyon

Epoch 45  →  V.Acc: %67.6
Epoch 60  →  V.Acc: ~%70
Parametre : 195.976
```

---

## 🗂️ Proje Yapısı

```
football_analysis/
│
├── gnn_buildup_model.py   # 22 oyunculu GNN model sınıfı
├── train.py               # Sekans bazlı eğitim scripti
├── predict.py             # Terminal üzerinden tahmin
├── main.py                # FastAPI backend
├── database.py            # Veritabanı bağlantısı
├── load_events.py         # StatsBomb event yükleyici
├── load_freeze_frames.py  # Freeze-frame yükleyici
├── load_matches.py        # Maç verisi yükleyici
├── best_model_v2.pt       # Eğitilmiş model ağırlıkları
│
└── frontend/
    └── src/
        ├── Pages/
        │   └── BuildupAnalysis.jsx  # İnteraktif saha komponenti
        ├── Components/
        │   ├── MatchStats.js
        │   ├── LineupView.js
        │   ├── Pitch.js
        │   └── SequencePlayer.js
        └── App.js
```

---

## 🚀 Kurulum

### Gereksinimler

```
Python 3.10+
Node.js 18+
PostgreSQL 14+
```

### Backend Kurulumu

```bash
# Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # Linux/Mac

# Bağımlılıkları yükle
pip install fastapi uvicorn psycopg2-binary python-dotenv
pip install torch torch_geometric

# Ortam değişkenlerini ayarla
cp .env.example .env
# .env dosyasına DB_PASSWORD ekle
```

### Veritabanı Kurulumu

```bash
# StatsBomb verisini yükle
python load_matches.py
python load_events.py
python load_freeze_frames.py
```

### Frontend Kurulumu

```bash
cd frontend
npm install
```

---

## ▶️ Çalıştırma

**Terminal 1 — API:**
```bash
uvicorn main:app --reload
```

**Terminal 2 — Model Eğitimi:**
```bash
python train.py
```

**Terminal 3 — Frontend:**
```bash
cd frontend
npm start
```

Tarayıcıda `http://localhost:3000/buildup` adresine git.

---

## 🔌 API Endpointleri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/matches` | Tüm maçları listele |
| GET | `/matches/{id}/events` | Maç eventleri |
| GET | `/matches/{id}/sequences/{team}` | Takımın sekansları |
| GET | `/matches/{id}/stats` | Maç istatistikleri |
| GET | `/matches/{id}/lineup` | Kadro |
| GET | `/teams` | Tüm takımlar |
| GET | `/teams/{team}/stats` | Takım istatistikleri |
| GET | `/events/{id}/freeze-frames` | Event freeze-frame |
| POST | `/predict/buildup` | **GNN anlık tahmin** |

### `/predict/buildup` İstek Formatı

```json
{
  "players": [
    {"id": 1, "x": 8.0, "y": 40.0, "role": "keeper", "is_own": true},
    {"id": 12, "x": 112.0, "y": 40.0, "role": "keeper", "is_own": false}
  ],
  "my_team": "Spain",
  "opponent_team": "England",
  "score_diff": 1,
  "minute": 23
}
```

### Yanıt Formatı

```json
{
  "prediction": "Ilerleme",
  "confidence": 0.724,
  "probabilities": {
    "Tehlikeli Kayip": 0.031,
    "Notr Kayip": 0.142,
    "Ilerleme": 0.724,
    "Yuksek Tehlike": 0.103
  },
  "context": {
    "opp_pressure_index": 0.42,
    "own_territory": 0.61,
    "own_count": 11,
    "opp_count": 11
  }
}
```

---

## 📊 Koordinat Sistemi

StatsBomb koordinat sistemi kullanılmaktadır:

```
(0,0) ────────────────────────── (120,0)
  │                                  │
  │   Kendi Kale    Orta    Rakip    │
  │      x=0        x=60   Kale     │
  │                         x=120   │
(0,80) ─────────────────────── (120,80)

Ceza sahası sınırı: x=102
Orta saha:          x=60
```

---

## 🛠️ Geliştirme Yol Haritası

- [x] Temel GNN modeli (11 oyuncu)
- [x] 22 oyunculu heterojen graf mimarisi
- [x] Sekans bazlı doğru etiketleme
- [x] İnteraktif saha arayüzü
- [x] Rakip baskı modelleme
- [ ] Rakip oyuncu özelinde pas analizi
- [ ] Expected Threat (xT) entegrasyonu
- [ ] Isı haritası görselleştirme
- [ ] Baskı şeması varyasyon analizi
- [ ] Oyuncu karşılaştırma paneli

---

## 📦 Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Model | PyTorch, PyTorch Geometric |
| Backend | FastAPI, PostgreSQL, psycopg2 |
| Frontend | React, SVG |
| Veri | StatsBomb Open Data |

---

## 📄 Veri Kaynağı

Bu proje [StatsBomb Open Data](https://github.com/statsbomb/open-data) kullanmaktadır.

```
StatsBomb tarafından sağlanan veriler
© StatsBomb Services Ltd.
Eğitim ve araştırma amaçlı kullanım için ücretsizdir.
```

---

## 👤 Geliştirici

**Emre Kargıllı**  
[GitHub](https://github.com/EmreKrglle/FootballAnalysis)
