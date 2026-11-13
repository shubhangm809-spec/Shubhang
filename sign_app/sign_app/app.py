import os
import cv2
import joblib
import numpy as np
import threading
import queue
from collections import deque

from utils import (
    detect_hands,
    normalize_landmarks,
    close_detector
)

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


# =========================================================
# SETTINGS
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(
    BASE_DIR, "models", "sign_model.pkl"
)

DISPLAY_CONFIDENCE = 0.50
SPEECH_CONFIDENCE = 0.75

HOLD_FRAMES = 18
STABILITY_THRESHOLD = 0.85
UNLOCK_FRAMES = 8

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720


# =========================================================
# LOAD MODEL
# =========================================================

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        "Model not found. Run python train.py first."
    )

model = joblib.load(MODEL_PATH)

if not hasattr(model, "predict_proba"):
    close_detector()
    raise RuntimeError(
        "The model must support predict_proba()."
    )

EXPECTED_FEATURES = getattr(
    model, "n_features_in_", 126
)

if EXPECTED_FEATURES != 126:
    close_detector()
    raise ValueError(
        f"Model expects {EXPECTED_FEATURES} features, "
        "but utils.py produces 126. "
        "Retrain using the matching dataset format."
    )

print("=" * 45)
print("SIGNOVA SIGN LANGUAGE TRANSLATOR")
print("=" * 45)
print("Model loaded.")
print("Classes:", model.classes_)
print("Display threshold:", DISPLAY_CONFIDENCE)
print("Speech threshold:", SPEECH_CONFIDENCE)


# =========================================================
# SPEECH WORKER
# =========================================================

speech_queue = queue.Queue()


def speech_worker():
    if pyttsx3 is None:
        print("pyttsx3 is not installed. Voice is disabled.")
        return

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 145)

        while True:
            text = speech_queue.get()

            try:
                if text is None:
                    return

                engine.say(text)
                engine.runAndWait()

            except Exception as error:
                print("Speech error:", error)

            finally:
                speech_queue.task_done()

    except Exception as error:
        print("Could not start speech engine:", error)


if pyttsx3 is not None:
    threading.Thread(
        target=speech_worker,
        daemon=True
    ).start()


def speak(text):
    if text and pyttsx3 is not None:
        speech_queue.put(text)


# =========================================================
# SENTENCE STORAGE
# =========================================================

words = []


def get_sentence():
    if not words:
        return ""

    return " ".join(words).replace("_", " ").capitalize()


# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    close_detector()
    raise RuntimeError(
        "Cannot open camera. Close other camera applications."
    )

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

cv2.namedWindow(
    "SIGNOVA TRANSLATOR",
    cv2.WINDOW_NORMAL
)

cv2.resizeWindow(
    "SIGNOVA TRANSLATOR",
    1100,
    750
)


# =========================================================
# RECOGNITION STATE
# =========================================================

prediction_history = deque(maxlen=HOLD_FRAMES)

locked_word = None
frames_without_hands = 0


# =========================================================
# MAIN LOOP
# =========================================================

try:
    while True:

        ok, frame = cap.read()

        if not ok:
            print("Camera frame error.")
            break

        frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        result = detect_hands(rgb)

        hands = result.hand_landmarks or []
        hand_count = len(hands)

        current_word = ""
        current_confidence = 0.0
        stable_word = None
        stable_confidence = 0.0

        # -------------------------------------------------
        # HAND DETECTION
        # -------------------------------------------------

        if hand_count > 0:

            frames_without_hands = 0

            h, w = frame.shape[:2]

            for hand in hands:
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

            # ---------------------------------------------
            # PREDICTION
            # ---------------------------------------------

            features = normalize_landmarks(result)

            if features is not None:

                features = np.asarray(
                    features,
                    dtype=np.float32
                ).flatten()

                if len(features) == EXPECTED_FEATURES:

                    probabilities = model.predict_proba(
                        [features]
                    )[0]

                    best_index = int(
                        np.argmax(probabilities)
                    )

                    current_confidence = float(
                        probabilities[best_index]
                    )

                    predicted_word = str(
                        model.classes_[best_index]
                    )

                    if current_confidence >= DISPLAY_CONFIDENCE:

                        current_word = predicted_word

                        prediction_history.append(
                            (
                                predicted_word,
                                current_confidence
                            )
                        )

                    else:
                        prediction_history.clear()

                else:
                    prediction_history.clear()

            else:
                prediction_history.clear()

        else:

            frames_without_hands += 1
            prediction_history.clear()

            if frames_without_hands >= UNLOCK_FRAMES:
                locked_word = None

        # -------------------------------------------------
        # STABILITY AND AVERAGE CONFIDENCE
        # -------------------------------------------------

        if len(prediction_history) == HOLD_FRAMES:

            history_words = [
                item[0] for item in prediction_history
            ]

            values, counts = np.unique(
                history_words,
                return_counts=True
            )

            best_index = int(np.argmax(counts))
            candidate = str(values[best_index])

            stability = counts[best_index] / HOLD_FRAMES

            candidate_confidences = [
                conf
                for word, conf in prediction_history
                if word == candidate
            ]

            average_confidence = float(
                np.mean(candidate_confidences)
            )

            if (
                stability >= STABILITY_THRESHOLD
                and average_confidence >= SPEECH_CONFIDENCE
            ):
                stable_word = candidate
                stable_confidence = average_confidence

        # -------------------------------------------------
        # ACCEPT AND SPEAK ONCE
        # -------------------------------------------------

        if stable_word is not None and locked_word != stable_word:

            words.append(stable_word)
            locked_word = stable_word

            speak(
                stable_word.replace("_", " ")
            )

            print(
                f"Accepted: {stable_word} | "
                f"Average confidence: "
                f"{stable_confidence * 100:.1f}%"
            )

        # -------------------------------------------------
        # SINGLE TEXT DISPLAY
        # -------------------------------------------------

        h, w = frame.shape[:2]

        cv2.rectangle(
            frame,
            (0, 0),
            (w, 85),
            (15, 15, 15),
            -1
        )

        cv2.putText(
            frame,
            "SIGNOVA - SIGN LANGUAGE TRANSLATOR",
            (20, 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.rectangle(
            frame,
            (0, 85),
            (w, 180),
            (30, 30, 30),
            -1
        )

        sentence = get_sentence()
        display_text = sentence

        # Candidate is shown in the same text area.
        # It is not spoken until accepted.
        if current_word and stable_word is None:

            candidate_text = current_word.replace("_", " ")

            if sentence:
                display_text = sentence + " | " + candidate_text
            else:
                display_text = candidate_text

        cv2.putText(
            frame,
            "TEXT:",
            (20, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2
        )

        max_chars = max(1, int((w - 150) / 15))
        visible_text = display_text[-max_chars:]

        cv2.putText(
            frame,
            visible_text,
            (100, 145),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.rectangle(
            frame,
            (0, h - 45),
            (w, h),
            (15, 15, 15),
            -1
        )

        cv2.putText(
            frame,
            "C Clear   B Backspace   S Speak   Q Quit",
            (20, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1
        )

        cv2.imshow(
            "SIGNOVA TRANSLATOR",
            frame
        )

        # -------------------------------------------------
        # KEYBOARD
        # -------------------------------------------------

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord("c"):

            words.clear()
            locked_word = None
            prediction_history.clear()

            print("Text cleared.")

        elif key == ord("b"):

            if words:
                words.pop()

            locked_word = None
            prediction_history.clear()

            print("Last word removed.")

        elif key == ord("s"):

            sentence = get_sentence()

            if sentence:
                speak(sentence)

finally:
    cap.release()
    cv2.destroyAllWindows()
    close_detector()

    if pyttsx3 is not None:
        speech_queue.put(None)

print("Signova application closed.")