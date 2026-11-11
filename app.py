import os
import time
import math
import threading
import collections
import numpy as np
import cv2
import torch
import mediapipe as mp
from datetime import datetime
from flask import Flask, render_template, request, Response, redirect, url_for, jsonify, flash, session, make_response
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from ultralytics import YOLO
from models import db, User, TranslationSession, TranslationHistory

# --- BYPASS PYTORCH SECURITY (for compatibility) ---
original_load = torch.load
torch.load = lambda *args, **kwargs: original_load(*args, **{**kwargs, 'weights_only': False})

# --- LOAD MODELS ---
MODEL_PATH = "bisindo.pt"
model_object_detection = YOLO(MODEL_PATH)

from PIL import Image
from transformers import pipeline
try:
    hf_sign_pipeline = pipeline("image-classification", model="RavenOnur/Sign-Language")
    print("[AI Model] Pipeline Hugging Face (RavenOnur/Sign-Language) aktif ✓")
except Exception as e:
    print(f"[AI Model Warning] Hugging Face pipeline gagal dimuat: {e}")
    hf_sign_pipeline = None

# --- DATABASE CONFIG (XAMPP MySQL with Auto-Creation & SQLite Fallback) ---
def get_database_uri():
    try:
        import pymysql
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='', connect_timeout=3)
        with conn.cursor() as cur:
            cur.execute("CREATE DATABASE IF NOT EXISTS signlanguage_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
        print("[Database] Terhubung ke MySQL XAMPP (signlanguage_db) ✓")
        return 'mysql+pymysql://root:@127.0.0.1:3306/signlanguage_db?charset=utf8mb4'
    except Exception as e:
        print(f"[Database Warning] MySQL XAMPP tidak dapat dijangkau: {e}. Menggunakan SQLite fallback.")
        return 'sqlite:///signlanguage.db'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'slt_super_secret_key_2025_bismillah'
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Silakan login terlebih dahulu.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()


# =============================================================================
# ASYNCHRONOUS DB LOGGER (NON-BLOCKING)
# =============================================================================
def _async_save_history(session_id, word, conf):
    """Save detected word asynchronously to prevent blocking the video frame generator."""
    def _worker():
        try:
            with app.app_context():
                hist = TranslationHistory(
                    session_id=session_id,
                    word=word,
                    confidence=conf
                )
                db.session.add(hist)
                sess_obj = TranslationSession.query.get(session_id)
                if sess_obj:
                    sess_obj.word_count = (sess_obj.word_count or 0) + 1
                db.session.commit()
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


# Global camera settings state
_streamer_settings = {
    'flipH': True,
    'detect': True,
    'mediaPipe': True,
    'confidence': 10.0,
    'engine': 'hybrid'  # 'hybrid', 'hf', 'yolo'
}


VALID_ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def is_anatomically_consistent(cand_letter, lm):
    """
    Validates if a candidate letter from YOLO is physically consistent with the 3D hand skeleton.
    Prevents YOLO hallucinations (e.g. YOLO falsely detecting 'V' or 'O' on a closed fist).
    """
    import math
    def d(i1, i2): return math.hypot(lm[i1].x - lm[i2].x, lm[i1].y - lm[i2].y)
    palm = max(d(0, 9), 0.001)

    i_open = (d(8, 0) / max(d(5, 0), 0.001) > 1.25) and (d(8, 5) / palm > 0.55)
    m_open = (d(12, 0) / max(d(9, 0), 0.001) > 1.25) and (d(12, 9) / palm > 0.55)
    r_open = (d(16, 0) / max(d(13, 0), 0.001) > 1.25) and (d(16, 13) / palm > 0.55)
    p_open = (d(20, 0) / max(d(17, 0), 0.001) > 1.25) and (d(20, 17) / palm > 0.55)
    open_count = sum([i_open, m_open, r_open, p_open])
    thb_open = (d(4, 9) / palm > 0.80) or (d(4, 17) / palm > 1.05)

    cand = cand_letter.upper().strip()
    if cand in ('A', 'E', 'S', 'T', 'M', 'N'):
        return open_count == 0 or (open_count == 1 and not (i_open or m_open))
    elif cand in ('D', 'G', 'L', 'Q', 'X', 'Z'):
        return i_open and open_count <= 2
    elif cand in ('I', 'J'):
        return p_open and not i_open and not m_open
    elif cand == 'Y':
        return p_open and thb_open and not i_open and not m_open
    elif cand in ('V', 'U', 'R', 'K', 'H', 'P'):
        return i_open and (m_open or d(4, 12) / palm < 0.35) and not r_open and not p_open
    elif cand == 'W':
        return i_open and m_open and r_open and not p_open
    elif cand in ('B', 'C', 'F', 'O'):
        return open_count >= 2
    return True


def evaluate_hand_geometry(lm):
    """
    Evaluates 3D landmark structural geometry strictly for Alphabet A–Z letters.
    Uses scale-invariant hand normalization (relative to palm size dist(0, 9)).
    Designed for maximum precision and natural human hand adaptability.
    """
    import math
    def dist(i1, i2):
        if isinstance(i1, int):
            p1, p2 = lm[i1], lm[i2]
        else:
            p1, p2 = i1, i2
        return math.hypot(p1.x - p2.x, p1.y - p2.y)

    palm_size = max(dist(0, 9), 0.001)

    # 1. Extension ratios (wrist to tip vs wrist to mcp)
    i_ext = dist(8, 0) / max(dist(5, 0), 0.001)
    m_ext = dist(12, 0) / max(dist(9, 0), 0.001)
    r_ext = dist(16, 0) / max(dist(13, 0), 0.001)
    p_ext = dist(20, 0) / max(dist(17, 0), 0.001)

    # 2. Tip to MCP ratios (finger self-length, highly invariant to tilt/perspective)
    d8_5   = dist(8, 5) / palm_size
    d12_9  = dist(12, 9) / palm_size
    d16_13 = dist(16, 13) / palm_size
    d20_17 = dist(20, 17) / palm_size

    # 3. Robust open / closed finger classification
    idx_open   = (i_ext > 1.28) and (d8_5 > 0.55)
    mid_open   = (m_ext > 1.28) and (d12_9 > 0.55)
    rng_open   = (r_ext > 1.28) and (d16_13 > 0.55)
    pky_open   = (p_ext > 1.28) and (d20_17 > 0.55)

    idx_closed = (i_ext < 1.20) or (d8_5 < 0.52)
    mid_closed = (m_ext < 1.20) or (d12_9 < 0.52)
    rng_closed = (r_ext < 1.20) or (d16_13 < 0.52)
    pky_closed = (p_ext < 1.20) or (d20_17 < 0.52)

    # Fist detection: all 4 fingers curled or folded
    all_closed = (idx_closed and mid_closed and rng_closed and pky_closed) or (
        d8_5 < 0.55 and d12_9 < 0.55 and d16_13 < 0.55 and d20_17 < 0.55
    )

    # Thumb metrics
    thb_ext = dist(4, 9) / palm_size
    d4_8    = dist(4, 8) / palm_size
    d4_12   = dist(4, 12) / palm_size
    d4_16   = dist(4, 16) / palm_size
    d4_17   = dist(4, 17) / palm_size
    d4_6    = dist(4, 6) / palm_size
    d4_10   = dist(4, 10) / palm_size
    d8_12   = dist(8, 12) / palm_size

    # Thumb direction & states
    thb_y_6 = (lm[4].y - lm[6].y) / palm_size
    thb_up  = (lm[4].y < lm[3].y) and (lm[4].y < lm[2].y)
    thb_open = (thb_ext > 0.82) or (d4_17 > 1.08)

    # Direction vectors for index finger
    idx_dy = (lm[8].y - lm[5].y) / palm_size
    idx_dx = (lm[8].x - lm[5].x) / palm_size
    idx_up = idx_dy < -0.32
    idx_horiz = (abs(idx_dx) > 0.75 * max(abs(idx_dy), 0.01)) and (abs(idx_dx) > 0.38)

    # Hooked index finger check (X gesture)
    idx_hooked = (i_ext > 1.22) and (dist(6, 0) > dist(5, 0) * 1.08) and (
        (lm[8].z - lm[5].z < -0.08) or (dist(8, 0) <= dist(7, 0) * 1.08)
    )

    # =========================================================================
    # 1. SPECIAL PINCH / CIRCLE GESTURES (F, O)
    # =========================================================================
    # F: OK gesture - Thumb tip touches Index tip (d4_8 < 0.28), other 3 fingers open
    if d4_8 < 0.28 and d4_12 > 0.42 and mid_open and rng_open and pky_open:
        return 'F', 97.0

    # O: Thumb touches Index and Middle tips forming circle, hollow interior
    if d4_8 < 0.38 and d4_12 < 0.38 and not all_closed:
        return 'O', 96.0

    # =========================================================================
    # 2. SINGLE FINGER EXTENSIONS (Y, I, J, X, L, Q, G, D, Z)
    # =========================================================================
    # Y: Shaka - Thumb and Pinky open, index/mid/rng closed
    if thb_open and pky_open and idx_closed and mid_closed and rng_closed:
        return 'Y', 96.0

    # I / J: Pinky only open upright, others closed, thumb tucked
    if pky_open and idx_closed and mid_closed and rng_closed and not thb_open:
        if (lm[20].x - lm[17].x) < -0.28 * palm_size:
            return 'J', 94.0
        return 'I', 96.0

    # X: Hooked index finger (bent claw), others closed
    if idx_hooked and mid_closed and rng_closed and pky_closed and not thb_open:
        return 'X', 95.0

    # L: Index upright + Thumb perpendicular outward (wide gap d4_8 > 1.15)
    if thb_open and idx_open and mid_closed and rng_closed and pky_closed:
        if idx_up and not idx_horiz and d4_8 > 1.15:
            return 'L', 96.0

    # Q: Index and thumb pointing downward
    # G: Index pointing horizontally, thumb pointing up/perpendicular
    if thb_open and idx_open and mid_closed and rng_closed and pky_closed:
        if idx_dy > 0.18:
            return 'Q', 95.0
        elif idx_horiz:
            return 'G', 95.0

    # D / Z: Index only open upright (straight, not hooked)
    if idx_open and not idx_hooked and idx_up:
        if d4_12 < 0.35:
            return 'D', 96.0
        elif abs(idx_dx) > 0.42 and mid_closed and rng_closed and pky_closed:
            return 'Z', 94.0
        elif mid_closed and rng_closed and not thb_open:
            return 'D', 95.0

    # =========================================================================
    # 3. C-SHAPE (Arched fingers facing thumb with open gap)
    # =========================================================================
    if d4_17 > 0.65 and (0.35 <= d4_8 <= 1.45) and (0.35 <= d4_12 <= 1.50):
        if d8_12 < 0.45 and not all_closed:
            if not (idx_open and mid_closed and rng_closed and pky_closed):
                return 'C', 96.0

    # =========================================================================
    # 4. CLOSED FIST VARIATIONS (A, E, S, M, N, T)
    # =========================================================================
    # T: Thumb tucked between index and middle
    if (idx_closed or i_ext < 1.35) and mid_closed and rng_closed and pky_closed:
        if d4_17 > 0.85 and (0.38 <= d4_6 < 0.68) and thb_y_6 > 0.18:
            return 'T', 94.0

    if all_closed:
        # A: Thumb straight UP along outer edge of index
        if thb_y_6 <= 0.15 and d4_17 > 0.80 and d4_6 < 0.55:
            return 'A', 96.0

        # M / N: Thumb tucked under fingers
        if d4_8 < 0.45:
            if d4_17 < 0.60:
                return 'M', 93.0
            else:
                return 'N', 93.0

        # S: Thumb folded across the FRONT of fingers (over middle finger knuckle 10)
        if d4_10 < 0.48 and d4_17 < 0.70:
            return 'S', 95.0

        # E: All 4 fingers curled down, thumb tucked flat underneath fingertips across palm
        if thb_y_6 > 0.18 and d4_17 < 0.55:
            return 'E', 96.0

    # =========================================================================
    # 5. TWO FINGERS (V, U, R, K, H, P)
    # =========================================================================
    if idx_open and (mid_open or d4_12 < 0.25):
        # P: pointing downward or thumb touches middle
        if (idx_dy > -0.18 and d4_12 < 0.35) or (d4_12 < 0.20 and idx_dx < -0.48):
            return 'P', 94.0

        # H: pointing horizontally
        if idx_horiz and mid_open and rng_closed and pky_closed:
            return 'H', 95.0

        # R: Crossed fingers
        if mid_open and rng_closed and pky_closed:
            base_diff = lm[5].x - lm[9].x
            tip_diff  = lm[8].x - lm[12].x
            if (base_diff * tip_diff < 0) or (d8_12 < 0.16):
                return 'R', 95.0

        # K: Thumb tip placed between or at base of middle finger knuckle 10
        if mid_open and rng_closed and pky_closed and (d4_10 < 0.42 or d4_6 < 0.45):
            return 'K', 95.0

        # V: Fingers spread apart
        if mid_open and rng_closed and pky_closed and d8_12 > 0.30:
            return 'V', 96.0
        # U: Fingers held together
        elif mid_open and rng_closed and pky_closed:
            return 'U', 95.0

    # =========================================================================
    # 6. THREE FINGERS (W)
    # =========================================================================
    if idx_open and mid_open and rng_open and pky_closed and not thb_open:
        return 'W', 96.0

    # =========================================================================
    # 7. FOUR FINGERS (B)
    # =========================================================================
    if idx_open and mid_open and rng_open and pky_open and not thb_open:
        return 'B', 96.0

    return None, None


# =============================================================================
# VIDEO STREAMING CLASS — High Performance with Smoothing Buffer
# =============================================================================
class VideoStreaming:
    """
    High-Performance VideoStreaming with:
    - 640x480 resolution & hardware MJPG at 30 FPS
    - Precision MediaPipe 3D Hand Tracking (model_complexity=1)
    - Dynamic Gesture Tracker (Kinematic Trajectory for Halo, Pagi, Malam, etc.)
    - Hybrid AI Detection (Geometry Heuristics + Vision Transformer + YOLO BISINDO)
    - Shared Singleton Camera Worker thread
    - Smoothing buffer & anti-flicker
    - Non-blocking asynchronous database persistence
    """

    BUFFER_SIZE = 2   # Fast, anti-jitter smoothing buffer
    MIN_VOTES   = 2   # 2 consecutive frames confirms letter (~130ms)

    def __init__(self):
        self._flipH      = _streamer_settings.get('flipH', True)
        self._detect     = _streamer_settings.get('detect', True)
        self._mediaPipe  = _streamer_settings.get('mediaPipe', True)
        self._confidence = _streamer_settings.get('confidence', 35.0)

        # MediaPipe hands — high-precision model_complexity=1 with resilient tracking
        self.mp_hands   = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands      = self.mp_hands.Hands(
            model_complexity=1,
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.45,
            min_tracking_confidence=0.45
        )

        # Smoothing buffer
        self._label_buffer      = collections.deque(maxlen=self.BUFFER_SIZE)
        self._last_emitted      = None
        self._last_emitted_time = 0

        # Shared singleton camera & inference worker
        self._lock               = threading.Lock()
        self._client_lock        = threading.Lock()
        self._latest_jpeg        = None
        self._latest_frame_time  = 0
        self._active_clients     = 0
        self._worker_thread      = None
        self._running            = False
        self._current_session_id = None

    @property
    def confidence(self): return self._confidence
    @confidence.setter
    def confidence(self, value): self._confidence = float(value)

    @property
    def flipH(self): return self._flipH
    @flipH.setter
    def flipH(self, value): self._flipH = bool(value)

    @property
    def detect(self): return self._detect
    @detect.setter
    def detect(self, value): self._detect = bool(value)

    @property
    def mediaPipe(self): return self._mediaPipe
    @mediaPipe.setter
    def mediaPipe(self, value): self._mediaPipe = bool(value)

    def _get_smoothed_label(self, current_label, current_conf):
        """
        Majority voting over the last BUFFER_SIZE frames for A-Z alphabet.
        Returns (label, conf) only if there's a clear majority,
        and only if it differs from the last emitted label (or cooldown passed).
        """
        import time
        now = time.time()

        if current_label not in VALID_ALPHABET and current_label != '__none__':
            return None, None

        self._label_buffer.append((current_label, current_conf))

        if len(self._label_buffer) < self.BUFFER_SIZE:
            return None, None

        # Count votes
        votes = collections.Counter(item[0] for item in self._label_buffer)
        top_label, top_count = votes.most_common(1)[0]

        if top_label == '__none__' or top_label not in VALID_ALPHABET:
            self._last_emitted = None
            return None, None

        if top_count < self.MIN_VOTES:
            return None, None  # No strong consensus

        # Average confidence for the winning label
        avg_conf = float(np.mean([c for l, c in self._label_buffer if l == top_label]))

        now = time.time()
        if top_label == self._last_emitted:
            if now - self._last_emitted_time > 0.45:
                self._last_emitted_time = now
                self._label_buffer.clear()
                return top_label, avg_conf
            return None, None  # Same as last — don't re-emit continuously

        self._last_emitted = top_label
        self._last_emitted_time = now
        self._label_buffer.clear()
        return top_label, avg_conf

    def _open_camera(self):
        """Open camera with automatic fallback and retries if hardware is busy."""
        import time
        for attempt in range(4):
            for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY]:
                for idx in [0, 1]:
                    try:
                        cap = cv2.VideoCapture(idx, backend)
                        if cap.isOpened():
                            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            cap.set(cv2.CAP_PROP_FPS, 30)
                            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            ret, frame = cap.read()
                            if ret and frame is not None:
                                return cap
                            cap.release()
                    except Exception:
                        pass
            time.sleep(0.2)
        return None

    def _ensure_worker(self):
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._running = True
                self._worker_thread = threading.Thread(target=self._camera_worker, daemon=True)
                self._worker_thread.start()

    def _camera_worker(self):
        """Background thread: runs camera capture & AI inference once for all connected web clients."""
        import time
        cap = None
        frame_idx = 0
        cached_boxes = []
        fail_count = 0

        while self._running:
            with self._client_lock:
                clients = self._active_clients

            # If no web clients connected for > 15s, release camera so other apps can use it
            if clients <= 0 and (time.time() - self._latest_frame_time > 15.0):
                if cap and cap.isOpened():
                    cap.release()
                    cap = None
                time.sleep(0.2)
                continue

            # Ensure hardware camera is opened
            if cap is None or not cap.isOpened():
                cap = self._open_camera()
                if cap is None or not cap.isOpened():
                    blank = np.zeros((480, 640, 3), np.uint8)
                    cv2.putText(blank, "Kamera Sedang Menghubungkan...", (110, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2)
                    _, buf = cv2.imencode('.jpg', blank)
                    with self._lock:
                        self._latest_jpeg = buf.tobytes()
                        self._latest_frame_time = time.time()
                    time.sleep(0.4)
                    continue

            ok, frame = cap.read()
            if not ok or frame is None:
                fail_count += 1
                if fail_count > 20:
                    if cap:
                        cap.release()
                        cap = None
                    fail_count = 0
                time.sleep(0.03)
                continue
            fail_count = 0
            frame_idx += 1

            flip_h     = _streamer_settings.get('flipH', self._flipH)
            do_detect  = _streamer_settings.get('detect', self._detect)
            do_mp      = _streamer_settings.get('mediaPipe', self._mediaPipe)
            conf_val   = _streamer_settings.get('confidence', self._confidence)
            engine     = _streamer_settings.get('engine', 'hybrid')

            if flip_h:
                frame = cv2.flip(frame, 1)

            h, w, _ = frame.shape
            mp_result = None

            # --- MediaPipe Hand Skeleton Tracking ---
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_result = self.hands.process(rgb)
                if do_mp and mp_result and mp_result.multi_hand_landmarks:
                    for hl in mp_result.multi_hand_landmarks:
                        self.mp_drawing.draw_landmarks(
                            frame, hl, self.mp_hands.HAND_CONNECTIONS,
                            self.mp_drawing.DrawingSpec(color=(220, 220, 220), thickness=2, circle_radius=3),
                            self.mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2, circle_radius=2)
                        )
            except Exception:
                pass

            # --- MULTI-ENGINE HAND GESTURE DETECTION (A–Z ALPHABET ONLY) ---
            if do_detect:
                if frame_idx % 2 == 0:
                    new_boxes = []

                    # 1. Static Hand Geometry & Vision Transformer
                    if engine in ('hybrid', 'hf') and mp_result and mp_result.multi_hand_landmarks:
                        for hl in mp_result.multi_hand_landmarks:
                            xmin_raw = min([lm.x for lm in hl.landmark])
                            xmax_raw = max([lm.x for lm in hl.landmark])
                            ymin_raw = min([lm.y for lm in hl.landmark])
                            ymax_raw = max([lm.y for lm in hl.landmark])

                            cx = (xmin_raw + xmax_raw) / 2.0
                            cy = (ymin_raw + ymax_raw) / 2.0
                            half_side = max(xmax_raw - xmin_raw, ymax_raw - ymin_raw) * 0.65

                            xmin = max(int((cx - half_side) * w), 0)
                            ymin = max(int((cy - half_side) * h), 0)
                            xmax = min(int((cx + half_side) * w), w)
                            ymax = min(int((cy + half_side) * h), h)

                            # Level 1: Static 3D Landmark Geometry (Letters A, B, C, D, E, F, I, K, L, O, R, S, U, V, W, Y)
                            geom_label, geom_conf = evaluate_hand_geometry(hl.landmark)
                            if geom_label and geom_label in VALID_ALPHABET:
                                new_boxes.append((xmin, ymin, xmax, ymax, geom_label, geom_conf))
                            elif hf_sign_pipeline:
                                hand_crop = frame[ymin:ymax, xmin:xmax]
                                if hand_crop.size > 0:
                                    try:
                                        pil_crop = Image.fromarray(cv2.cvtColor(hand_crop, cv2.COLOR_BGR2RGB))
                                        preds = hf_sign_pipeline(pil_crop)
                                        if preds:
                                            top_p = preds[0]
                                            p_label = top_p['label'].upper().strip()
                                            p_conf = float(top_p['score']) * 100.0
                                            hf_min_conf = max(5.0, float(conf_val) * 0.5 if float(conf_val) > 10 else 5.0)
                                            if p_label in VALID_ALPHABET and p_conf >= hf_min_conf:
                                                new_boxes.append((xmin, ymin, xmax, ymax, p_label, p_conf))
                                    except Exception:
                                        pass

                    # 2. YOLO BISINDO Object Detection (Letters A–Z)
                    if engine in ('hybrid', 'yolo'):
                        yolo_th = max(0.40, float(conf_val) / 100.0 if float(conf_val) > 10 else 0.40)
                        try:
                            results = model_object_detection.predict(
                                frame, imgsz=640, conf=yolo_th, verbose=False
                            )
                            if len(results[0].boxes) > 0:
                                for b in results[0].boxes:
                                    bx1, by1, bx2, by2 = map(int, b.xyxy[0])
                                    bcls = int(b.cls[0])
                                    bconf = float(b.conf[0]) * 100.0
                                    raw_name = model_object_detection.names[bcls]
                                    clean_name = raw_name.upper().strip()

                                    if clean_name in VALID_ALPHABET:
                                        # Verify anatomical plausibility against tracked hand skeleton
                                        if mp_result and mp_result.multi_hand_landmarks:
                                            first_hl = mp_result.multi_hand_landmarks[0]
                                            if not is_anatomically_consistent(clean_name, first_hl.landmark):
                                                continue  # Skip physically impossible hallucination

                                        # Synergy: if geometry also found this letter, boost confidence
                                        matched_idx = -1
                                        for idx_b, eb in enumerate(new_boxes):
                                            if eb[4] == clean_name:
                                                matched_idx = idx_b
                                                break
                                        if matched_idx >= 0:
                                            old_b = new_boxes[matched_idx]
                                            new_boxes[matched_idx] = (old_b[0], old_b[1], old_b[2], old_b[3], clean_name, min(99.0, max(old_b[5], bconf) + 4.0))
                                        else:
                                            has_high_geom = any(b[5] >= 95.0 and b[4] in VALID_ALPHABET for b in new_boxes)
                                            if not has_high_geom or engine == 'yolo':
                                                new_boxes.append((bx1, by1, bx2, by2, clean_name, bconf))
                        except Exception:
                            pass

                    # Filter strictly to VALID_ALPHABET (A-Z only)
                    valid_boxes = [b for b in new_boxes if b[4] in VALID_ALPHABET]

                    if len(valid_boxes) > 0:
                        best = max(valid_boxes, key=lambda b: b[5])

                        # Instant live detection emission (zero-latency for practice and live HUD)
                        socketio.emit('live_detection', {
                            'word':       best[4],
                            'confidence': round(best[5], 1),
                            'session_id': self._current_session_id
                        })

                        smooth_label, smooth_conf = self._get_smoothed_label(best[4], best[5] / 100.0)

                        if smooth_label and smooth_label in VALID_ALPHABET:
                            payload = {
                                'word':       smooth_label,
                                'confidence': round(smooth_conf * 100, 1),
                                'session_id': self._current_session_id
                            }
                            socketio.emit('detection', payload)

                            if self._current_session_id:
                                _async_save_history(self._current_session_id, smooth_label, smooth_conf)

                        cached_boxes = valid_boxes
                    else:
                        cached_boxes = []
                        self._get_smoothed_label('__none__', 0.0)

                for (bx1, by1, bx2, by2, bname, bconf) in cached_boxes:
                    if bname in VALID_ALPHABET:
                        cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 255, 255), 2)
                        tag = f"{bname} {bconf:.0f}%"
                        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                        tag_y = max(22, by1)
                        cv2.rectangle(frame, (bx1, tag_y - 22), (bx1 + tw + 10, tag_y + 2), (20, 20, 20), -1)
                        cv2.putText(frame, tag, (bx1 + 5, tag_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cached_boxes = []

            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            with self._lock:
                self._latest_jpeg = buf.tobytes()
                self._latest_frame_time = time.time()

            time.sleep(0.015)

        if cap and cap.isOpened():
            cap.release()

    def stream(self, session_id=None):
        """Generator: yields shared MJPEG frames with instant connect and high FPS."""
        import time
        if session_id:
            self._current_session_id = session_id

        self._ensure_worker()
        with self._client_lock:
            self._active_clients += 1

        last_sent = 0
        try:
            while True:
                with self._lock:
                    jpeg = self._latest_jpeg
                    ftime = self._latest_frame_time

                if jpeg is not None and ftime != last_sent:
                    last_sent = ftime
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'

                time.sleep(0.025)
        finally:
            with self._client_lock:
                self._active_clients = max(0, self._active_clients - 1)


# Singleton VideoStreaming Instance
global_streamer = VideoStreaming()


# =============================================================================
# ROUTES — PUBLIC
# =============================================================================

@app.route('/')
def homepage():
    return render_template('hompage.html')


@app.route('/dev_autologin')
def dev_autologin():
    user = User.query.first()
    if user:
        login_user(user)
    target = request.args.get('next', '/dashboard')
    return redirect(target)


@app.route('/dictionary')
@app.route('/kamus')
def dictionary():
    return render_template('dictionary.html')


# =============================================================================
# ROUTES — AUTH
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            flash('Selamat datang kembali, ' + user.username + '!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Email atau password salah.', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username  = request.form.get('username', '').strip()
        email     = request.form.get('email', '').strip()
        password  = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        errors = []
        if not username or len(username) < 3:
            errors.append('Username minimal 3 karakter.')
        if not email or '@' not in email:
            errors.append('Email tidak valid.')
        if not password or len(password) < 6:
            errors.append('Password minimal 6 karakter.')
        if password != password2:
            errors.append('Konfirmasi password tidak cocok.')
        if User.query.filter_by(username=username).first():
            errors.append('Username sudah digunakan.')
        if User.query.filter_by(email=email).first():
            errors.append('Email sudah terdaftar.')

        if errors:
            for e in errors:
                flash(e, 'error')
        else:
            colors = ['#7c3aed','#8b5cf6','#a855f7','#ec4899','#6366f1']
            import random
            user = User(
                username=username,
                email=email,
                avatar_color=random.choice(colors)
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash('Akun berhasil dibuat! Selamat datang, ' + username + '!', 'success')
            return redirect(url_for('dashboard'))

    return render_template('register.html')


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        step = request.form.get('step', 'find')

        if step == 'find':
            email = request.form.get('email', '').strip()
            user = User.query.filter_by(email=email).first()
            if user:
                return render_template('forgot_password.html',
                                       step='reset', found_user=user)
            else:
                flash('Email tidak ditemukan. Pastikan email yang kamu masukkan benar.', 'error')
                return render_template('forgot_password.html', step='find')

        elif step == 'reset':
            user_id = request.form.get('user_id', type=int)
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            user = User.query.get(user_id)
            if not user:
                flash('Akun tidak ditemukan.', 'error')
                return render_template('forgot_password.html', step='find')

            if len(new_password) < 6:
                flash('Password minimal 6 karakter.', 'error')
                return render_template('forgot_password.html',
                                       step='reset', found_user=user)

            if new_password != confirm_password:
                flash('Konfirmasi password tidak cocok.', 'error')
                return render_template('forgot_password.html',
                                       step='reset', found_user=user)

            user.set_password(new_password)
            db.session.commit()
            return render_template('forgot_password.html', step='done')

    return render_template('forgot_password.html', step='find')


@app.route('/logout')
@login_required
def logout():
    # Close any open sessions
    open_sessions = TranslationSession.query.filter_by(
        user_id=current_user.id, ended_at=None
    ).all()
    for s in open_sessions:
        s.ended_at = datetime.utcnow()
    db.session.commit()
    logout_user()
    flash('Berhasil logout.', 'success')
    return redirect(url_for('homepage'))


# =============================================================================
# ROUTES — PRACTICE & QUIZ
# =============================================================================

@app.route('/practice')
@login_required
def practice():
    return render_template('practice.html')


@app.route('/api/practice/score', methods=['POST'])
@login_required
def save_practice_score():
    data = request.get_json() or {}
    score = int(data.get('score', 0))
    streak = int(data.get('streak', 0))
    if score > (current_user.practice_score or 0):
        current_user.practice_score = score
    if streak > (current_user.practice_streak or 0):
        current_user.practice_streak = streak
    db.session.commit()
    return jsonify({'status': 'ok', 'score': current_user.practice_score, 'streak': current_user.practice_streak})


# =============================================================================
# ROUTES — PROFILE & SETTINGS
# =============================================================================

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            new_username = request.form.get('username', '').strip()
            new_email = request.form.get('email', '').strip()
            avatar_color = request.form.get('avatar_color', current_user.avatar_color)

            if len(new_username) < 3:
                flash('Username minimal 3 karakter.', 'error')
            elif '@' not in new_email:
                flash('Email tidak valid.', 'error')
            else:
                existing_user = User.query.filter(User.username == new_username, User.id != current_user.id).first()
                existing_email = User.query.filter(User.email == new_email, User.id != current_user.id).first()
                if existing_user:
                    flash('Username sudah digunakan oleh akun lain.', 'error')
                elif existing_email:
                    flash('Email sudah terdaftar pada akun lain.', 'error')
                else:
                    current_user.username = new_username
                    current_user.email = new_email
                    current_user.avatar_color = avatar_color
                    db.session.commit()
                    flash('Profil berhasil diperbarui!', 'success')

        elif action == 'change_password':
            old_pass = request.form.get('old_password', '')
            new_pass = request.form.get('new_password', '')
            conf_pass = request.form.get('confirm_password', '')

            if not current_user.check_password(old_pass):
                flash('Password lama salah.', 'error')
            elif len(new_pass) < 6:
                flash('Password baru minimal 6 karakter.', 'error')
            elif new_pass != conf_pass:
                flash('Konfirmasi password baru tidak cocok.', 'error')

            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash('Password berhasil diubah!', 'success')

        return redirect(url_for('profile'))

    return render_template('profile.html')


# =============================================================================
# ROUTES — DASHBOARD & HISTORY
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    recent_sessions = TranslationSession.query.filter_by(
        user_id=current_user.id
    ).order_by(TranslationSession.started_at.desc()).limit(5).all()

    # Top words
    from sqlalchemy import func
    top_words = db.session.query(
        TranslationHistory.word,
        func.count(TranslationHistory.word).label('count')
    ).join(TranslationSession).filter(
        TranslationSession.user_id == current_user.id
    ).group_by(TranslationHistory.word).order_by(
        func.count(TranslationHistory.word).desc()
    ).limit(5).all()

    return render_template('dashboard.html',
                           recent_sessions=recent_sessions,
                           top_words=top_words)


@app.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    sessions = TranslationSession.query.filter_by(
        user_id=current_user.id
    ).order_by(TranslationSession.started_at.desc()).paginate(page=page, per_page=10)
    return render_template('history.html', sessions=sessions)


@app.route('/api/session/<int:session_id>/words')
@login_required
def session_words(session_id):
    sess = TranslationSession.query.filter_by(
        id=session_id, user_id=current_user.id
    ).first_or_404()
    words = [{'word': w.word, 'confidence': w.confidence,
               'time': w.detected_at.strftime('%H:%M:%S')}
             for w in sess.words]
    return jsonify(words)


@app.route('/api/history/export')
@login_required
def api_history_export():
    import csv, io
    sessions = TranslationSession.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Session ID', 'Tanggal', 'Jumlah Kata', 'Hasil Terjemahan'])
    for s in sessions:
        writer.writerow([s.id, s.started_at.strftime('%Y-%m-%d %H:%M'),
                         s.word_count or 0, s.result_text or ''])
    output.seek(0)
    resp = make_response(output.getvalue())
    resp.headers['Content-Disposition'] = 'attachment; filename=riwayat_terjemahan.csv'
    resp.headers['Content-Type'] = 'text/csv'
    return resp


# =============================================================================
# ROUTES — TRANSLATOR (MAIN APP)
# =============================================================================

@app.route('/translate')
@login_required
def translate():
    # Create a new translation session
    sess = TranslationSession(user_id=current_user.id)
    db.session.add(sess)
    db.session.commit()
    return render_template('index.html', session_id=sess.id)


@app.route('/dialog')
@login_required
def dialog():
    # Create a new interactive dialogue session
    sess = TranslationSession(user_id=current_user.id)
    db.session.add(sess)
    db.session.commit()
    return render_template('dialog.html', session_id=sess.id)


@app.route('/video_feed')
@login_required
def video_feed():
    session_id = request.args.get('session_id', None, type=int)
    return Response(
        global_streamer.stream(session_id=session_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    global _streamer_settings
    if request.method == 'POST':
        data = request.get_json() or {}
        _streamer_settings.update(data)
        return jsonify({'status': 'ok'})
    return jsonify(_streamer_settings)


@app.route('/api/session/<int:session_id>/save', methods=['POST'])
@login_required
def save_session_result(session_id):
    data = request.get_json() or {}
    sess = TranslationSession.query.filter_by(
        id=session_id, user_id=current_user.id
    ).first_or_404()
    sess.result_text = data.get('text', '')
    sess.ended_at    = datetime.utcnow()
    db.session.commit()
    return jsonify({'status': 'saved'})


# =============================================================================
# SOCKETIO EVENTS
# =============================================================================

@socketio.on('connect')
def on_connect():
    pass

@socketio.on('ping_server')
def on_ping():
    socketio.emit('pong_client', {'status': 'connected'})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002, debug=False, allow_unsafe_werkzeug=True)