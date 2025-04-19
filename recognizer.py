import cv2
import os
import numpy as np
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity
import time
from db.db import Log, session, Worker
import pickle

def nothing(x):
    pass

# تحميل نموذج التعرف على الوجه (بـ CPU)
face_model = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_model.prepare(ctx_id=0, det_size=(640, 640))

# تحميل الوجوه المعروفة
def load_known_faces(known_faces_path):
    known_embeddings = []
    known_names = []

    for person_name in os.listdir(known_faces_path):
        person_folder = os.path.join(known_faces_path, person_name)
        if not os.path.isdir(person_folder):
            continue

        for filename in os.listdir(person_folder):
            img_path = os.path.join(person_folder, filename)
            img = cv2.imread(img_path)
            if img is None:
                print(f"Failed to load image: {img_path}")
                continue

            faces = face_model.get(img)
            if len(faces) > 0:
                embedding = faces[0].embedding
                known_embeddings.append(embedding)
                known_names.append(person_name)
            else:
                print(f"No faces detected in {img_path}")

    if not known_embeddings:
        print("Warning: No known faces loaded.")
        return [], []

    return known_embeddings, known_names

# حفظ الـ embeddings في ملف باستخدام pickle
def save_embeddings(known_embeddings, known_names, filepath="known_faces_embeddings.pkl"):
    data = {
        "embeddings": known_embeddings,
        "names": known_names
    }
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)
    print(f"Saved embeddings to {filepath}")

# تحميل الـ embeddings من ملف pickle
def load_embeddings(filepath="known_faces_embeddings.pkl"):
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        print(f"Loaded embeddings from {filepath}")
        return data["embeddings"], data["names"]
    else:
        return [], []

# محاولة تحميل الـ embeddings من الملف أولاً
known_faces_path = "known_faces"
known_embeddings, known_names = load_embeddings()

# إذا لم تكن هناك embeddings محفوظة، قم بتحميل الوجوه المعروفة من المجلد
if not known_embeddings:
    known_embeddings, known_names = load_known_faces(known_faces_path)
    if known_embeddings:  # إذا تم تحميل الوجوه بنجاح
        save_embeddings(known_embeddings, known_names)
else:
    print("Using pre-loaded embeddings.")

# فتح الكاميرا
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

# ضبط دقة الكاميرا
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# إنشاء نافذة للفيديو
cv2.namedWindow("Face Recognition with Zone", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Face Recognition with Zone", 640, 480)

# إنشاء نافذة للسلايدرات
cv2.namedWindow("Controls", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Controls", 400, 200)

# إنشاء Trackbars في نافذة Controls
cv2.createTrackbar("Left", "Controls", 0, 1000, nothing)
cv2.createTrackbar("Top", "Controls", 0, 1000, nothing)
cv2.createTrackbar("Width", "Controls", 200, 1000, nothing)
cv2.createTrackbar("Height", "Controls", 600, 1000, nothing)

tracked_faces = {}
disappear_timeout = 5

def check(name, first_coords, last_coords):
    if name == 'Unknown':
        return None
    if last_coords[0] < box_width - box_left:
        return True

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break

    frame_height, frame_width = frame.shape[:2]

    # قراءة القيم من التراكبارات
    box_left = cv2.getTrackbarPos("Left", "Controls")
    box_top = cv2.getTrackbarPos("Top", "Controls")
    box_width = cv2.getTrackbarPos("Width", "Controls")
    box_height = cv2.getTrackbarPos("Height", "Controls")

    # التأكد من أن القيم ضمن الحدود
    box_left = max(0, min(box_left, frame_width - 1))
    box_top = max(0, min(box_top, frame_height - 1))
    box_width = max(1, min(box_width, frame_width - box_left))
    box_height = max(1, min(box_height, frame_height - box_top))

    # رسم المربع الأزرق
    cv2.rectangle(frame, (box_left, box_top), (box_left + box_width, box_top + box_height), (255, 0, 0), 2)

    # اكتشاف الوجوه
    faces = face_model.get(frame)
    for face in faces:
        x1, y1, x2, y2 = map(int, face.bbox)
        emb = face.embedding.reshape(1, -1)
        face_cx = int((x1 + x2) / 2)
        face_cy = int((y1 + y2) / 2)

        # المقارنة مع الوجوه المعروفة
        sims = cosine_similarity(emb, np.array(known_embeddings))
        best_idx = np.argmax(sims)
        best_score = sims[0][best_idx]
        best_match_name = known_names[best_idx] if best_score > 0.4 else "Unknown"

        in_zone = box_left < face_cx < box_left + box_width and box_top < face_cy < box_top + box_height
        if best_match_name not in tracked_faces:
            tracked_faces[best_match_name] = {
                "first_seen": time.time(),
                "last_seen": time.time(),
                "first_coords": (x1, y1, x2, y2),
                "last_coords": (x1, y1, x2, y2)
            }
        else:
            tracked_faces[best_match_name]["last_seen"] = time.time()
            tracked_faces[best_match_name]["last_coords"] = (x1, y1, x2, y2)

        color = (0, 255, 0) if in_zone else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.circle(frame, (face_cx, face_cy), 5, (0, 255, 255), -1)
        cv2.putText(frame, f"{best_match_name}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # حذف الأشخاص بعد اختفائهم
    to_delete = []
    for name, data in tracked_faces.items():
        if time.time() - data["last_seen"] > disappear_timeout:
            if check(name, data['first_coords'], data['last_coords']):
                worker = session.query(Worker).filter_by(name=name).first()
                if not worker:
                    worker = Worker(name=name)
                    session.add(worker)
                    session.commit()

                log = Log(
                    worker_id=worker.id,
                    in_date=int(data['first_seen']),
                    out_date=int(data['last_seen'])
                )
                session.add(log)
                session.commit()
            to_delete.append(name)

    for name in to_delete:
        del tracked_faces[name]

    # عرض إطار الفيديو
    cv2.imshow("Face Recognition with Zone", frame)

    # اضغط على ESC أو 'q' للخروج
    key = cv2.waitKey(1) & 0xFF
    if key == 27 or key == ord('q'):
        break

# طباعة البيانات المتبقية
print("بيانات الأشخاص المتبقية:")
for name, data in tracked_faces.items():
    print(f"الشخص: {name}, أول ظهور: {data['first_seen']}, آخر ظهور: {data['last_seen']}, "
          f"إحداثيات أول ظهور: {data['first_coords']}, إحداثيات آخر ظهور: {data['last_coords']}")

cap.release()
cv2.destroyAllWindows()
