# 🤟 SignLanguage Translator (BISINDO AI)

> **Aplikasi Web Penerjemah Bahasa Isyarat Indonesia (BISINDO) Real-Time Menggunakan Hybrid Computer Vision dan 3D Hand Skeleton Tracking**  
> *Laporan Proyek Akhir — Disusun oleh: **Bimo Aditya Sasmito** (Kelas XII PPLG, SMK Negeri 1 Kota Bengkulu — TA 2026/2027)*

---

## 📌 Ringkasan Proyek

**SignLanguage Translator** adalah aplikasi web interaktif berbasis kecerdasan buatan (*Artificial Intelligence*) yang dirancang untuk menjembatani komunikasi antara penyandang disabilitas rungu/tuli (**Teman Tuli**) dan masyarakat umum (**Teman Dengar**).

Sistem ini mengimplementasikan pendekatan **Hybrid AI Architecture**:
1. **Google MediaPipe Hands 3D**: Ekstraksi 21 koordinat sendi tangan secara real-time dengan normalisasi ukuran telapak tangan invarian skala (*Scale-Invariant Palm Normalization*).
2. **Evaluasi Geometri Biomekanika Analitis**: Klasifikasi gestur presisi tinggi untuk 26 alfabet BISINDO (A–Z), termasuk penyelesaian gestur melengkung (huruf **C**) dan cakar telapak (huruf **E**).
3. **Ultralytics YOLOv8 (`bisindo.pt`)**: Deteksi objek citra berbasis *deep learning* yang diperkuat dengan *Anatomical Consistency Gate* guna mengeliminasi deteksi palsu (*false positives*).
4. **Majority Voting Smoothing Buffer**: Menghilangkan getaran deteksi (*flicker*) tanpa menimbulkan jeda/latensi (~50 ms via WebSocket SocketIO).

---

## ✨ Fitur Utama

- 🎥 **Studio Penerjemah Real-Time (`/translate`)**: Feed kamera 30 FPS dengan overlay kerangka sendi tangan, deteksi alfabet otomatis, pembentukan kata/kalimat, serta pembaca suara **Text-to-Speech (TTS)** otomatis.
- 🎯 **Mode Latihan & Kuis Gamifikasi (`/practice`)**: Arena pembelajaran alfabet interaktif dengan target acak, penghitung skor, rekor *streak*, umpan balik instan, dan animasi perayaan konfeti.
- 💬 **Panggung Dialog Dua Arah Inklusif (`/dialog`)**: Komunikasi dua kanal:
  - *Kanal Teman Tuli*: Input isyarat kamera dikonversi menjadi teks dan suara.
  - *Kanal Teman Dengar*: Input teks/suara mikrofon dikonversi menjadi urutan kartu foto isyarat visual.
- 📖 **Kamus Digital Visual 26 Alfabet A–Z (`/dictionary`)**: Galeri kartu huruf alfabet lengkap dengan foto peraga nyata, pencarian cepat, navigasi abjad, modal detail tips jari, dan pelafalan audio.
- 📊 **Dashboard Analitik & Statistik (`/dashboard`)**: Ringkasan personal mencakup total kata terjemahan, jumlah sesi, skor kuis tertinggi, dan grafik huruf yang paling sering diisyaratkan.
- 📜 **Riwayat Sesi & Ekspor CSV (`/history`)**: Rekam jejak arsip terjemahan dan fitur unduh data lengkap format CSV.
- 🔐 **Autentikasi Akun Aman**: Enkripsi hash kata sandi PBKDF2-SHA256, proteksi sesi `@login_required`, serta alur pemulihan kata sandi mandiri (`/forgot-password`).

---

## 🛠️ Tumpukan Teknologi (Tech Stack)

| Komponen | Teknologi |
| :--- | :--- |
| **Backend & Routing** | Python 3.10+, Flask 3.0, Werkzeug |
| **Real-Time Streaming** | Flask-SocketIO (WebSocket Event-Driven) |
| **Computer Vision** | OpenCV (`cv2`), Google MediaPipe Hands 3D |
| **Deep Learning** | Ultralytics YOLOv8 (`bisindo.pt`), Hugging Face Transformers |
| **Basis Data** | Flask-SQLAlchemy (MySQL XAMPP port 3306 dengan Fallback Otomatis ke SQLite3) |
| **Frontend UI/UX** | HTML5, Tailwind CSS, FontAwesome 6, Canvas-Confetti, Responsive Dark Slate Theme |

---

## 📂 Struktur Direktori

```text
FINALREVISIAJA/
├── app.py                      # Core Backend, Routing, Vision Pipeline, & SocketIO
├── camera_settings.py          # Konfigurasi hardware webcam OpenCV
├── models.py                   # Skema Basis Data SQLAlchemy (User, Session, History)
├── bisindo.pt                  # Bobot Model Deep Learning YOLOv8 BISINDO
├── requirements.txt            # Daftar dependensi pustaka Python
├── signlanguage_db.sql         # Skrip dump struktur basis data MySQL
├── static/                     # Aset statis frontend
│   ├── style.css               # Desain antarmuka Dark Slate modern
│   ├── script.js              # Logika interaksi frontend umum
│   └── img/                    # Grafis & foto peraga asli (A.jpg s.d. Z.jpg)
├── templates/                  # Template HTML Jinja2
│   ├── base.html               # Master layout
│   ├── hompage.html            # Landing page publik
│   ├── login.html / register.html / forgot_password.html
│   ├── dashboard.html          # Panel kendali metrik statistik
│   ├── index.html              # Studio penerjemah kamera real-time
│   ├── practice.html           # Arena latihan & kuis interaktif
│   ├── dialog.html             # Panggung komunikasi dua arah
│   ├── dictionary.html         # Kamus visual 26 alfabet A–Z
│   ├── history.html            # Arsip riwayat sesi & ekspor data
│   └── profile.html            # Pengaturan profil pengguna
└── _pics/                      # Dokumentasi diagram arsitektur & screenshot aplikasi
```

---

## 🚀 Panduan Instalasi & Menjalankan

### 1. Kloning Repositori
```bash
git clone https://github.com/<username>/<nama-repo>.git
cd <nama-repo>
```

### 2. Buat Lingkungan Virtual Python
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Basis Data (Opsional)
- Aplikasi secara otomatis menggunakan **SQLite** (`instance/signlanguage.db`).
- Jika menggunakan **MySQL (XAMPP)**, nyalakan modul MySQL di XAMPP Control Panel, lalu buat database `signlanguage_db` dan impor berkas `signlanguage_db.sql`.

### 5. Jalankan Aplikasi
```bash
python app.py
```
Aplikasi akan aktif di: **`http://127.0.0.1:5002`**

---

## 👨‍💻 Pengembang

* **Nama:** Bimo Aditya Sasmito
* **Jurusan:** Pengembangan Perangkat Lunak dan Gim (PPLG)
* **Sekolah:** SMK Negeri 1 Kota Bengkulu
* **Tahun Ajaran:** 2026/2027
