import cv2
from deepface import DeepFace
import numpy as np
import time

# List of camera indexes (you can add more: [0, 1, 2])
CAMERA_INDEXES = [0]

# Global captures
captured_A = None
captured_B = None
last_result = None

# Haar cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def put_text(img, text, y=30, color=(255, 255, 255)):
    cv2.putText(img, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)

def detect_faces(frame):
    """Detect faces and return bounding boxes."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return faces

def crop_face(frame, box):
    """Crop face region from frame given bounding box."""
    x, y, w, h = box
    return frame[y:y+h, x:x+w]

def verify_faces(imgA, imgB):
    """Returns (is_same_person: bool, distance: float, model: str)."""
    result = DeepFace.verify(
        img1_path=imgA[:, :, ::-1],  # BGR->RGB
        img2_path=imgB[:, :, ::-1],
        model_name='Facenet512',
        detector_backend='opencv',
        enforce_detection=False
    )
    return bool(result['verified']), float(result['distance']), result.get('model', 'Facenet512')

def main():
    global captured_A, captured_B, last_result

    # Open all cameras
    caps = [cv2.VideoCapture(idx, cv2.CAP_DSHOW) for idx in CAMERA_INDEXES]
    for i, cap in enumerate(caps):
        if not cap.isOpened():
            print(f"❌ Could not open camera {CAMERA_INDEXES[i]}")

    while True:
        for i, cap in enumerate(caps):
            ok, frame = cap.read()
            if not ok:
                continue

            frame = cv2.flip(frame, 1)  # mirror for natural view
            faces = detect_faces(frame)

            # Draw bounding boxes
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            # Status display
            status = f"A: {'OK' if captured_A is not None else '—'} | B: {'OK' if captured_B is not None else '—'}"
            put_text(frame, status, y=30)
            put_text(frame, "Keys: 1=Capture A, 2=Capture B, R=Reset, Q=Quit", y=60)

            # Show last comparison result overlay
            if last_result is not None:
                is_same, dist, model, t = last_result
                if time.time() - t < 5:  # show for 5 seconds
                    msg = f"Match: {'YES' if is_same else 'NO'} | Dist: {dist:.4f} | Model: {model}"
                    color = (0, 200, 0) if is_same else (0, 0, 255)
                    put_text(frame, msg, y=100, color=color)

            cv2.imshow(f"Camera {i}", frame)

        # Key controls
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('1'):
            # Capture A from first detected face (from first available cam)
            for cap in caps:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                faces = detect_faces(frame)
                if len(faces) > 0:
                    captured_A = crop_face(frame, faces[0])
                    cv2.imwrite("face_A.jpg", captured_A)
                    print("✅ Captured face A -> face_A.jpg")
                    last_result = None
                    break
        elif key == ord('2'):
            # Capture B and compare
            for cap in caps:
                ok, frame = cap.read()
                if not ok:
                    continue
                frame = cv2.flip(frame, 1)
                faces = detect_faces(frame)
                if len(faces) > 0:
                    captured_B = crop_face(frame, faces[0])
                    cv2.imwrite("face_B.jpg", captured_B)
                    print("✅ Captured face B -> face_B.jpg")

                    if captured_A is not None and captured_B is not None:
                        try:
                            same, dist, model = verify_faces(captured_A, captured_B)
                            print(f"➡️ Match: {same} | Distance: {dist:.4f} | Model: {model}")
                            last_result = (same, dist, model, time.time())
                        except Exception as e:
                            print("❌ Verification error:", e)
                    break
        elif key == ord('r'):
            captured_A, captured_B, last_result = None, None, None
            print("🔄 Reset A & B.")

    # Release all
    for cap in caps:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
