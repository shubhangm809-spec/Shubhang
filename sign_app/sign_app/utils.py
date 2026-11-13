import os
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# =========================================================
# MEDIAPIPE HAND LANDMARKER
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "hand_landmarker.task")

BaseOptions = python.BaseOptions

options = vision.HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=MODEL_PATH
    ),
    num_hands=2,
    min_hand_detection_confidence=0.6,
    min_hand_presence_confidence=0.6,
    min_tracking_confidence=0.6,
)

hand_detector = vision.HandLandmarker.create_from_options(
    options
)


def detect_hands(frame_rgb):
    """Detect up to two hands from an RGB image."""

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=np.ascontiguousarray(frame_rgb)
    )

    return hand_detector.detect(mp_image)


def normalize_hand(hand_landmarks):
    """Convert 21 landmarks into 63 normalized features."""

    points = np.array(
        [[lm.x, lm.y, lm.z] for lm in hand_landmarks],
        dtype=np.float32
    )

    # Make the wrist the origin.
    points -= points[0]

    # Normalize scale using the XY coordinates.
    scale = np.max(
        np.linalg.norm(points[:, :2], axis=1)
    )

    if scale == 0:
        scale = 1.0

    points /= scale

    return points.flatten()


def normalize_landmarks(result):
    """
    One hand: 63 features plus 63 zeros.
    Two hands: 126 features.

    Always returns exactly 126 features.
    """

    if not result.hand_landmarks:
        return None

    features = []

    for hand in result.hand_landmarks[:2]:
        features.extend(normalize_hand(hand))

    while len(features) < 126:
        features.extend([0.0] * 63)

    return np.asarray(
        features[:126],
        dtype=np.float32
    )


def close_detector():
    """Release MediaPipe resources."""

    hand_detector.close()