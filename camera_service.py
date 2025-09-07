import cv2
import face_recognition
import os
import time
from app import app, db, MissingPerson, User, send_found_email

def start_camera():
    cap = cv2.VideoCapture(1)  # Use 0 for default camera

    # Keep track of emails already sent to avoid spamming
    notified_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        with app.app_context():
            persons = MissingPerson.query.all()

            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                name_label = "Unknown"

                for person in persons:
                    if not os.path.exists(person.image):
                        continue

                    try:
                        known_image = face_recognition.load_image_file(person.image)
                        known_encoding = face_recognition.face_encodings(known_image)[0]
                    except Exception as e:
                        print(f"Error loading image for {person.name}: {e}")
                        continue

                    matches = face_recognition.compare_faces([known_encoding], face_encoding)
                    if True in matches:
                        name_label = person.name

                        # If person not already marked found, mark and send mail
                        if person.status != "found":
                            person.status = "found"
                            db.session.commit()

                            owner = User.query.get(person.owner_id)
                            if person.id not in notified_ids:
                                send_found_email(owner.email, person.name)
                                print(f"✅ {person.name} Found! Email sent to {owner.email}")
                                notified_ids.add(person.id)
                        break

                # Draw rectangle and label
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(frame, name_label, (left, top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        cv2.imshow("Missing Person Finder Camera", frame)

        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    start_camera()
