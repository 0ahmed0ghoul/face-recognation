





import cv2
import os
import sys
import numpy as np
import time
import threading
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity
from collections import deque
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.db import Log, Worker, session
# ---------- CONFIG ----------
USE_GPU = True
SKIP_FRAMES = 1
USE_RESIZING = True
RESIZE_SCALE = 0.5
DISAPPEAR_TIMEOUT = 5
TARGET_FPS = 6  # <<< Added this

fps_queue = deque(maxlen=10)
last_fps_time = time.time()

# ---------- SETUP MODEL ----------
providers = ['CUDAExecutionProvider'] if USE_GPU else ['CPUExecutionProvider']
face_model = FaceAnalysis(name='buffalo_s', providers=providers)
face_model.prepare(ctx_id=0, det_size=(640, 640))

# ---------- LOAD KNOWN FACES ----------
def load_known_faces(known_faces_path="known_faces"):
    known_embeddings = []
    known_names = []

    print(f"[DEBUG] Loading known faces from: {known_faces_path}")

    for person_name in os.listdir(known_faces_path):
        person_folder = os.path.join(known_faces_path, person_name)
        if not os.path.isdir(person_folder):
            continue

        for filename in os.listdir(person_folder):
            img_path = os.path.join(person_folder, filename)
            img = cv2.imread(img_path)
            if img is None:
                print(f"[WARNING] Could not load image: {img_path}")
                continue

            faces = face_model.get(img)
            if faces:
                known_embeddings.append(faces[0].embedding)
                known_names.append(person_name)
                print(f"[INFO] Added face for {person_name}")
            else:
                print(f"[WARNING] No face detected in: {img_path}")

    print(f"[RESULT] Total known faces loaded: {len(known_embeddings)}")
    return known_embeddings, known_names

known_embeddings, known_names = load_known_faces()

# ---------- VIDEO CAPTURE THREAD ----------
class VideoCaptureThread:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.ret, self.frame = self.cap.read()
        self.running = True
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while self.running:
            self.ret, self.frame = self.cap.read()

    def read(self):
        return self.ret, self.frame

    def release(self):
        self.running = False
        self.cap.release()

# ---------- ENTRY CHECK ----------
def check_entry(name, first_coords, last_coords):
    if name == 'Unknown':
        return None
    if last_coords[0] < box_width - box_left:
        return True
    return False

# ---------- MAIN LOGIC ----------
cap = VideoCaptureThread()
box_left, box_top, box_width, box_height = 0, 0, 200, 600
tracked_faces = {}
frame_count = 0

while True:
    frame_start_time = time.time()

    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    if frame_count % (SKIP_FRAMES + 1) != 0:
        continue

    frame_display = frame.copy()
    if USE_RESIZING:
        small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_SCALE, fy=RESIZE_SCALE)
        faces = face_model.get(small_frame)
    else:
        faces = face_model.get(frame)

    frame_height, frame_width = frame.shape[:2]
    cv2.rectangle(frame_display, (box_left, box_top), (box_left + box_width, box_top + box_height), (255, 0, 0), 2)

    for face in faces:
        x1, y1, x2, y2 = [int(c / RESIZE_SCALE) for c in face.bbox] if USE_RESIZING else map(int, face.bbox)
        face_cx = (x1 + x2) // 2
        face_cy = (y1 + y2) // 2

        emb = face.embedding.reshape(1, -1)
        if len(known_embeddings) == 0:
            print("No known embeddings found!")
        else:
            sims = cosine_similarity(emb, np.array(known_embeddings))
        best_idx = np.argmax(sims)
        best_score = sims[0][best_idx]
        best_name = known_names[best_idx] if best_score > 0.5 else "Unknown"

        in_zone = box_left < face_cx < box_left + box_width and box_top < face_cy < box_top + box_height
        status_text = "inside" if in_zone else "outside"
        color = (0, 255, 0) if in_zone else (0, 0, 255)

        if best_name not in tracked_faces:
            tracked_faces[best_name] = {
                "first_seen": time.time(),
                "last_seen": time.time(),
                "first_coords": (x1, y1, x2, y2),
                "last_coords": (x1, y1, x2, y2)
            }
        else:
            tracked_faces[best_name]["last_seen"] = time.time()
            tracked_faces[best_name]["last_coords"] = (x1, y1, x2, y2)

        cv2.rectangle(frame_display, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame_display, (face_cx, face_cy), 5, (0, 255, 255), -1)
        cv2.putText(frame_display, f"{best_name} ({best_score:.2f}) - {status_text}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Handle timeout and logging
    to_remove = []
    for name, data in tracked_faces.items():
        if time.time() - data["last_seen"] > DISAPPEAR_TIMEOUT:
            if check_entry(name, data["first_coords"], data["last_coords"]):
                worker = session.query(Worker).filter_by(name=name).first()
                if not worker:
                    worker = Worker(name=name)
                    session.add(worker)
                    session.commit()
                log = Log(worker_id=worker.id, in_date=int(data["first_seen"]), out_date=int(data["last_seen"]))
                session.add(log)
                session.commit()
            to_remove.append(name)

    for name in to_remove:
        del tracked_faces[name]

    # FPS Counter
    now = time.time()
    fps = 1.0 / (now - last_fps_time)
    fps_queue.append(fps)
    avg_fps = sum(fps_queue) / len(fps_queue)
    last_fps_time = now
    cv2.putText(frame_display, f"FPS: {avg_fps:.1f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

    cv2.imshow("Fast Face Recognition", frame_display)

    # Throttle FPS to 6
    frame_end_time = time.time()
    elapsed = frame_end_time - frame_start_time
    time_to_sleep = max(0, (1.0 / TARGET_FPS) - elapsed)
    time.sleep(time_to_sleep)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ---------- CLEANUP ----------
print("Remaining tracked faces:")
for name, data in tracked_faces.items():
    print(f"{name}: Last seen at {data['last_seen']}")
cap.release()
cv2.destroyAllWindows()
