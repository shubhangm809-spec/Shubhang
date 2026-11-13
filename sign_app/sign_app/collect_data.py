import os
import sys
import csv
import cv2

from utils import detect_hands, normalize_landmarks, close_detector


# =========================================================
# SETTINGS
# =========================================================

TARGET = 1000

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.csv")

os.makedirs(DATA_DIR, exist_ok=True)


# =========================================================
# LABEL
# =========================================================

if len(sys.argv) < 2:
    print("Usage: python collect_data.py LABEL")
    print("Example: python collect_data.py HI")
    raise SystemExit(1)

label = sys.argv[1].strip().upper()

if not label:
    raise SystemExit("Label cannot be empty.")


# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot open camera.")
    close_detector()
    raise SystemExit(1)

recording = False
count = 0
target_reached = False

print("=" * 40)
print("SIGNOVA DATA COLLECTION")
print("Label:", label)
print("Target:", TARGET, "frames")
print("Press R to start or stop recording.")
print("Press Q to quit.")
print("=" * 40)


# =========================================================
# RECORDING
# =========================================================

try:
    # Append mode preserves all previously collected data.
    with open(
        DATASET_PATH,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        while cap.isOpened():

            ok, frame = cap.read()

            if not ok:
                print("ERROR: Could not read camera frame.")
                break

            frame = cv2.flip(frame, 1)

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            result = detect_hands(rgb)

            # Save one row only when recording and
            # valid hand landmarks are available.
            if recording and result.hand_landmarks:

                features = normalize_landmarks(result)

                if features is not None and len(features) == 126:

                    writer.writerow(
                        [label] + features.tolist()
                    )

                    count += 1

                    # Periodically flush saved data to disk.
                    if count % 50 == 0:
                        file.flush()
                        print(f"Saved {count}/{TARGET}")

                    if count >= TARGET:
                        recording = False
                        target_reached = True
                        file.flush()

            # Draw detected landmarks.
            if result.hand_landmarks:
                h, w = frame.shape[:2]

                for hand in result.hand_landmarks:
                    for lm in hand:
                        x = int(lm.x * w)
                        y = int(lm.y * h)

                        cv2.circle(
                            frame,
                            (x, y),
                            4,
                            (0, 255, 0),
                            -1
                        )

            # Status bar.
            cv2.rectangle(
                frame,
                (0, 0),
                (w if result.hand_landmarks else frame.shape[1], 100),
                (0, 0, 0),
                -1
            )

            status = (
                "TARGET COMPLETE"
                if target_reached
                else "RECORDING"
                if recording
                else "PRESS R TO START"
            )

            cv2.putText(
                frame,
                f"{label}: {count}/{TARGET}",
                (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                status,
                (15, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2
            )

            cv2.imshow(
                "SIGNOVA DATA COLLECTION",
                frame
            )

            key = cv2.waitKey(1) & 0xFF

            if target_reached:
                break

            if key == ord("r"):
                recording = not recording

                print(
                    "Recording started."
                    if recording
                    else "Recording paused."
                )

            elif key == ord("q"):
                break

finally:
    cap.release()
    cv2.destroyAllWindows()
    close_detector()

print()
print(f"Saved {count} samples for {label}")
print("Dataset:", DATASET_PATH)