import cv2
import face_recognition
import os
import time
import uuid
from app import app, db, MissingPerson, User, mail
from flask_mail import Message


def start_camera():
    cap = cv2.VideoCapture(1)  # Use 0 for default camera

    # Keep track of emails already sent
    notified_ids = set()

    # ✅ PRELOAD encodings to avoid lag
    known_encodings = {}
    with app.app_context():
        persons = MissingPerson.query.all()
        for person in persons:
            if os.path.exists(person.image):
                try:
                    img = face_recognition.load_image_file(person.image)
                    encoding = face_recognition.face_encodings(img)[0]
                    known_encodings[person.id] = (encoding, person)
                except Exception as e:
                    print(f"Error encoding {person.name}: {e}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name_label = "Unknown"

            for pid, (known_encoding, person) in known_encodings.items():
                matches = face_recognition.compare_faces([known_encoding], face_encoding)

                if True in matches:
                    name_label = person.name

                    # If person not already marked found, mark and send mail
                    if person.status != "found":
                        with app.app_context():
                            person.status = "found"
                            db.session.commit()

                            owner = User.query.get(person.owner_id)
                            if person.id not in notified_ids:
                                # Save FULL FRAME snapshot
                                snapshot_filename = f"snapshot_{uuid.uuid4().hex}.jpg"
                                snapshot_path = os.path.join("static/uploads", snapshot_filename)
                                cv2.imwrite(snapshot_path, frame)

                                # Send email with attachment
                                try:
                                    msg = Message(
                                        subject=f"Missing Person Found: {person.name}",
                                        recipients=[owner.email],
                                        body=f"Good news! The missing person '{person.name}' has been found."
                                    )
                                    with open(snapshot_path, "rb") as f:
                                        msg.attach(snapshot_filename, "image/jpeg", f.read())
                                    mail.send(msg)
                                    print(f"✅ {person.name} Found! Email with full snapshot sent to {owner.email}")
                                except Exception as e:
                                    print(f"❌ Error sending email with snapshot: {e}")

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
