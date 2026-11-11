import os
import subprocess
import time
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

PICS_DIR = r"d:\FINALREVISIAJA\_pics"
os.makedirs(PICS_DIR, exist_ok=True)
CHROME_EXE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
TEMP_USER_DATA = r"C:\Users\bimoa\AppData\Local\Temp\chrome_report_shots"

# =============================================================================
# 1. GENERATE DIAGRAM: 02-FLOWCHART-PROGRAM.PNG
# =============================================================================
def make_flowchart(out_path):
    fig, ax = plt.subplots(figsize=(11, 14), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 140)
    ax.axis('off')
    fig.patch.set_facecolor('#ffffff')

    ax.text(50, 137, "DIAGRAM ALIR (FLOWCHART) SIGNLANGUAGE TRANSLATOR", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')
    ax.text(50, 134, "Alur Logika Program dari Inisialisasi Sesi, Inferensi Hybrid AI, hingga Respon Web", 
            ha='center', va='center', fontsize=9.5, fontstyle='italic', color='#475569')

    def draw_term(x, y, w, h, text, bg='#e2e8f0', ec='#475569'):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03", fc=bg, ec=ec, lw=1.5)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#0f172a')

    def draw_proc(x, y, w, h, text, sub="", bg='#ffffff', ec='#3b82f6'):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.01", fc=bg, ec=ec, lw=1.4)
        ax.add_patch(box)
        if sub:
            ax.text(x + w/2, y + h*0.65, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#0f172a')
            ax.text(x + w/2, y + h*0.35, sub, ha='center', va='center', fontsize=7.2, color='#475569')
        else:
            ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#0f172a')

    def draw_dec(x, y, w, h, text, bg='#fef3c7', ec='#d97706'):
        poly = patches.Polygon([[x+w/2, y], [x+w, y+h/2], [x+w/2, y+h], [x, y+h/2]], 
                               fc=bg, ec=ec, lw=1.4)
        ax.add_patch(poly)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=8, fontweight='bold', color='#92400e')

    def draw_arr(x1, y1, x2, y2, label=""):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color='#334155', lw=1.5, shrinkA=2, shrinkB=2))
        if label:
            ax.text((x1+x2)/2 + 1.5, (y1+y2)/2, label, fontsize=8, fontweight='bold', color='#1e293b')

    # Nodes
    draw_term(37.5, 126, 25, 5, "Mulai (Start)")
    draw_proc(35, 116, 30, 6, "Buka Aplikasi di Peramban", "URL: http://localhost:5002")
    draw_dec(37.5, 103, 25, 9, "Status Login\nAktif?")
    
    # Left branch (No login)
    draw_proc(5, 92, 28, 6, "Tampilkan Halaman Login", "Input Email & Password")
    draw_dec(6.5, 78, 25, 9, "Kredensial\nValid?")
    
    # Main Dashboard
    draw_proc(35, 90, 30, 6, "Tampilkan Dashboard Utama", "Pilih Menu Fitur Aplikasi")
    draw_proc(35, 79, 30, 6, "Inisialisasi Hardware Kamera", "Singleton MJPEG Worker 30 FPS")
    draw_proc(35, 68, 30, 6, "Tangkap Frame Video Kamera", "Resolusi 640x480 Piksel")
    draw_dec(37.5, 54, 25, 9, "Tangan\nTerdeteksi?")

    # AI Pipeline
    draw_proc(33, 41, 34, 8, "MediaPipe 3D Landmark & Normalisasi", "palm_size = dist(Wrist_0, MiddleMCP_9)")
    draw_proc(33, 29, 34, 8, "Evaluasi Geometri Anatomi + YOLOv8", "Klasifikasi 26 Alfabet A-Z (Boost 99%)")
    draw_proc(33, 17, 34, 7, "Majority Voting Smoothing Buffer", "Antrean 2 Frame & Cooldown 0.9s")
    draw_proc(33, 7, 34, 6, "Pancarkan Event WebSocket Socket.IO", "live_detection & detection")
    draw_term(37.5, 0.5, 25, 4.5, "Selesai (End)")

    # Arrows
    draw_arr(50, 126, 50, 122)
    draw_arr(50, 116, 50, 112)
    draw_arr(37.5, 107.5, 19, 98, "Tidak")
    draw_arr(50, 103, 50, 96, "Ya")
    draw_arr(19, 92, 19, 87)
    draw_arr(31.5, 82.5, 35, 93, "Ya")
    draw_arr(6.5, 82.5, 2, 82.5) # loopback
    ax.plot([2, 2, 19], [82.5, 100, 100], color='#334155', lw=1.5)
    ax.annotate('', xy=(19, 98), xytext=(19, 100), arrowprops=dict(arrowstyle="->", color='#334155', lw=1.5))
    ax.text(2.5, 92, "Tidak", fontsize=8, fontweight='bold', color='#dc2626')

    draw_arr(50, 90, 50, 85)
    draw_arr(50, 79, 50, 74)
    draw_arr(50, 68, 50, 63)
    draw_arr(50, 54, 50, 49, "Ya")
    
    # Loopback if no hand
    ax.plot([62.5, 75, 75], [58.5, 58.5, 71], color='#334155', lw=1.5)
    ax.annotate('', xy=(65, 71), xytext=(75, 71), arrowprops=dict(arrowstyle="->", color='#334155', lw=1.5))
    ax.text(64, 60, "Tidak", fontsize=8, fontweight='bold', color='#dc2626')

    draw_arr(50, 41, 50, 37)
    draw_arr(50, 29, 50, 24)
    draw_arr(50, 17, 50, 13)
    draw_arr(50, 7, 50, 5)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("Flowchart generated:", out_path)

# =============================================================================
# 2. GENERATE DIAGRAM: 03-ERD-DATABASE.PNG
# =============================================================================
def make_erd(out_path):
    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 70)
    ax.axis('off')
    fig.patch.set_facecolor('#ffffff')

    ax.text(50, 67, "DIAGRAM RELASI ENTITAS (ERD) BASIS DATA SIGNLANGUAGE TRANSLATOR", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0f172a')
    ax.text(50, 64, "Struktur Tabel users, translation_sessions, dan translation_history", 
            ha='center', va='center', fontsize=9.5, fontstyle='italic', color='#475569')

    def draw_entity(x, y, w, h, title, fields, bg_hdr='#3b82f6', bg_body='#ffffff'):
        hdr_h = 5.5
        box_hdr = patches.FancyBboxPatch((x, y + h - hdr_h), w, hdr_h, boxstyle="round,pad=0.01", fc=bg_hdr, ec=bg_hdr, lw=1)
        ax.add_patch(box_hdr)
        ax.text(x + w/2, y + h - hdr_h/2, title, ha='center', va='center', fontsize=10, fontweight='bold', color='#ffffff')

        box_body = patches.FancyBboxPatch((x, y), w, h - hdr_h, boxstyle="round,pad=0.01", fc=bg_body, ec='#cbd5e1', lw=1.5)
        ax.add_patch(box_body)

        curr_y = y + h - hdr_h - 3
        for fld in fields:
            ax.text(x + 2, curr_y, fld[0], fontsize=8.5, fontweight='bold' if 'PK' in fld[1] or 'FK' in fld[1] else 'normal', color='#0f172a')
            ax.text(x + w - 2, curr_y, fld[1], ha='right', fontsize=8, color='#2563eb' if 'PK' in fld[1] else ('#d97706' if 'FK' in fld[1] else '#64748b'))
            curr_y -= 3.2

    # Entity 1: users
    fields_u = [
        ("id", "INT [PK]"),
        ("username", "VARCHAR(80) UNIQUE"),
        ("email", "VARCHAR(120) UNIQUE"),
        ("password_hash", "VARCHAR(256)"),
        ("avatar_color", "VARCHAR(20)"),
        ("practice_score", "INT DEFAULT 0"),
        ("practice_streak", "INT DEFAULT 0"),
        ("created_at", "DATETIME")
    ]
    draw_entity(5, 26, 27, 33, "USERS", fields_u, bg_hdr='#1e3a8a')

    # Entity 2: translation_sessions
    fields_s = [
        ("id", "INT [PK]"),
        ("user_id", "INT [FK]"),
        ("started_at", "DATETIME"),
        ("ended_at", "DATETIME NULL"),
        ("word_count", "INT DEFAULT 0"),
        ("result_text", "TEXT")
    ]
    draw_entity(37.5, 30, 26, 27, "TRANSLATION_SESSIONS", fields_s, bg_hdr='#0284c7')

    # Entity 3: translation_history
    fields_h = [
        ("id", "INT [PK]"),
        ("session_id", "INT [FK]"),
        ("word", "VARCHAR(100)"),
        ("confidence", "FLOAT"),
        ("detected_at", "DATETIME")
    ]
    draw_entity(69, 32, 26, 24, "TRANSLATION_HISTORY", fields_h, bg_hdr='#059669')

    # Connecting relations
    def draw_rel(x1, y1, x2, y2, label="1 : N"):
        ax.plot([x1, x2], [y1, y2], color='#475569', lw=2)
        ax.text((x1+x2)/2, (y1+y2)/2 + 2, label, ha='center', fontsize=9, fontweight='bold', color='#1e293b')

    draw_rel(32, 42, 37.5, 42, "1 : N (Memiliki)")
    draw_rel(63.5, 42, 69, 42, "1 : N (Mencatat)")

    # Bottom notes
    box_n = patches.FancyBboxPatch((5, 5), 90, 15, boxstyle="round,pad=0.01", fc='#f8fafc', ec='#e2e8f0', lw=1.2)
    ax.add_patch(box_n)
    ax.text(7, 16.5, "Keterangan Relasi Integritas Data (Data Integrity Constraints):", fontsize=9, fontweight='bold', color='#334155')
    ax.text(7, 13.5, "• ON DELETE CASCADE: Jika akun User dihapus, seluruh riwayat sesi (sessions) otomatis terhapus bersih.", fontsize=8.5, color='#475569')
    ax.text(7, 10.5, "• ON DELETE CASCADE: Jika TranslationSession dihapus, detail kata terkait (history) ikut terhapus.", fontsize=8.5, color='#475569')
    ax.text(7, 7.5, "• Dual Persistence Mode: Terhubung ke MySQL XAMPP (Port 3306) dengan fallback otomatis ke SQLite lokal.", fontsize=8.5, color='#475569')

    plt.tight_layout()
    plt.savefig(out_path, dpi=200, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("ERD generated:", out_path)

# =============================================================================
# 3. CAPTURE WEB PAGES VIA CHROME HEADLESS
# =============================================================================
def capture_url(url, out_path, window_size="1280,800", delay=1.0):
    cmd = [
        CHROME_EXE,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={TEMP_USER_DATA}",
        f"--screenshot={out_path}",
        f"--window-size={window_size}",
        url
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    time.sleep(delay)
    if os.path.exists(out_path):
        print(f"Captured: {os.path.basename(out_path)} ({os.path.getsize(out_path)} bytes)")
    else:
        print(f"FAILED capturing: {url}")

# =============================================================================
# 4. COMPOSITE BUILDERS (SIDE-BY-SIDE & MULTI-VIEW)
# =============================================================================
def make_login_register_composite(out_path):
    p_login = os.path.join(PICS_DIR, "_tmp_login.png")
    p_reg = os.path.join(PICS_DIR, "_tmp_reg.png")
    capture_url("http://127.0.0.1:5002/login", p_login, window_size="900,700")
    capture_url("http://127.0.0.1:5002/register", p_reg, window_size="900,700")

    if os.path.exists(p_login) and os.path.exists(p_reg):
        im1 = Image.open(p_login)
        im2 = Image.open(p_reg)
        w, h = im1.size
        comp = Image.new("RGB", (w * 2 + 10, h), (241, 245, 249))
        comp.paste(im1, (0, 0))
        comp.paste(im2, (w + 10, 0))
        comp.save(out_path)
        print("Composite 05-login-register.png created!")
        try:
            os.remove(p_login)
            os.remove(p_reg)
        except: pass

def make_ce_detection_showcase(out_path):
    # Buat showcase presisi huruf C dan E dengan kartu foto asli dan hasil deteksi AI
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.5), dpi=200)
    fig.patch.set_facecolor('#0f172a')

    # Card 1: Huruf C
    c_img_path = r"d:\FINALREVISIAJA\static\img\signs\C.jpg"
    if os.path.exists(c_img_path):
        c_img = Image.open(c_img_path)
        axes[0].imshow(c_img)
    axes[0].axis('off')
    axes[0].set_title("DETEKSI PRESET: HURUF C (96.0% MATCH)\nBusur Melengkung 4 Jari & Ibu Jari Terbuka", 
                      color='#38bdf8', fontsize=10.5, fontweight='bold', pad=12)

    # Card 2: Huruf E
    e_img_path = r"d:\FINALREVISIAJA\static\img\signs\E.jpg"
    if os.path.exists(e_img_path):
        e_img = Image.open(e_img_path)
        axes[1].imshow(e_img)
    axes[1].axis('off')
    axes[1].set_title("DETEKSI PRESET: HURUF E (96.0% MATCH)\nCakar Rapat ke Telapak & Ibu Jari Mendatar", 
                      color='#38bdf8', fontsize=10.5, fontweight='bold', pad=12)

    plt.tight_layout()
    plt.savefig(out_path, dpi=200, facecolor=fig.get_facecolor(), bbox_inches='tight')
    plt.close()
    print("Showcase 08-deteksi-huruf-c-e.png created!")

if __name__ == '__main__':
    print("--- 1. Generating High-Res System Diagrams ---")
    make_flowchart(os.path.join(PICS_DIR, "02-flowchart-program.png"))
    make_erd(os.path.join(PICS_DIR, "03-erd-database.png"))

    print("\n--- 2. Capturing Real Web Application Pages ---")
    capture_url("http://127.0.0.1:5002/", os.path.join(PICS_DIR, "04-landing-page.png"))
    make_login_register_composite(os.path.join(PICS_DIR, "05-login-register.png"))
    capture_url("http://127.0.0.1:5002/dev_autologin?next=/dashboard", os.path.join(PICS_DIR, "06-dashboard-utama.png"))
    capture_url("http://127.0.0.1:5002/dev_autologin?next=/translate", os.path.join(PICS_DIR, "07-studio-penerjemah.png"))
    make_ce_detection_showcase(os.path.join(PICS_DIR, "08-deteksi-huruf-c-e.png"))
    capture_url("http://127.0.0.1:5002/dev_autologin?next=/practice", os.path.join(PICS_DIR, "09-mode-latihan.png"))
    capture_url("http://127.0.0.1:5002/dev_autologin?next=/dialog", os.path.join(PICS_DIR, "10-mode-dialog-dua-arah.png"))
    capture_url("http://127.0.0.1:5002/dictionary", os.path.join(PICS_DIR, "11-kamus-digital-a-z.png"))
    capture_url("http://127.0.0.1:5002/dev_autologin?next=/history", os.path.join(PICS_DIR, "12-riwayat-terjemahan.png"))

    print("\nAll assets generated successfully in _pics/!")
