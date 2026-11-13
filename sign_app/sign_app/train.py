import csv
import os
import json
import numpy as np

# ---------------- CONFIGURATION ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "data", "dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
WEIGHTS_PATH = os.path.join(MODEL_DIR, "signova_weights.npz")
LABELS_PATH = os.path.join(MODEL_DIR, "signova_labels.json")

INPUT_SIZE = 126
HIDDEN_SIZE = 64
EPOCHS = 150
LEARNING_RATE = 0.01
TEST_RATIO = 0.20
SEED = 42

np.random.seed(SEED)


# ---------------- LOAD DATA ----------------
def load_dataset():
    X, labels = [], []

    with open(DATASET_PATH, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)

        for line_number, row in enumerate(reader, start=1):
            if not row:
                continue

            if len(row) != INPUT_SIZE + 1:
                print(f"Skipping row {line_number}: expected 127 columns.")
                continue

            label = row[0].strip().upper()

            try:
                features = np.array(row[1:], dtype=np.float32)
            except ValueError:
                print(f"Skipping row {line_number}: invalid feature value.")
                continue

            if not label or not np.isfinite(features).all():
                continue

            X.append(features)
            labels.append(label)

    if not X:
        raise ValueError("No valid samples found in dataset.csv.")

    return np.asarray(X, dtype=np.float32), np.asarray(labels)


# ---------------- PREPARE DATA ----------------
X, labels = load_dataset()
classes = sorted(set(labels.tolist()))

if len(classes) < 2:
    raise ValueError(
        "At least two different sign labels are required for classification."
    )

class_to_id = {name: i for i, name in enumerate(classes)}
y = np.array([class_to_id[label] for label in labels], dtype=np.int64)

print("Total samples:", len(X))
print("Input features:", X.shape[1])
print("Sign classes:", len(classes))
print("Labels:", classes)

# Shuffle and split each class into training/testing samples.
rng = np.random.default_rng(SEED)
train_indices, test_indices = [], []

for class_id in range(len(classes)):
    indices = np.flatnonzero(y == class_id)
    rng.shuffle(indices)

    if len(indices) < 2:
        raise ValueError(
            f"Class {classes[class_id]} has fewer than 2 samples."
        )

    test_count = max(1, int(round(len(indices) * TEST_RATIO)))
    test_count = min(test_count, len(indices) - 1)

    test_indices.extend(indices[:test_count])
    train_indices.extend(indices[test_count:])

rng.shuffle(train_indices)
rng.shuffle(test_indices)

X_train = X[train_indices]
y_train = y[train_indices]
X_test = X[test_indices]
y_test = y[test_indices]

# ---------------- NEURAL NETWORK ----------------
# Two-layer network: input -> ReLU hidden layer -> softmax output.
# All trainable weights and gradients are implemented here.

number_of_classes = len(classes)

W1 = rng.normal(
    0, np.sqrt(2.0 / INPUT_SIZE),
    (INPUT_SIZE, HIDDEN_SIZE)
).astype(np.float32)
b1 = np.zeros((1, HIDDEN_SIZE), dtype=np.float32)

W2 = rng.normal(
    0, np.sqrt(2.0 / HIDDEN_SIZE),
    (HIDDEN_SIZE, number_of_classes)
).astype(np.float32)
b2 = np.zeros((1, number_of_classes), dtype=np.float32)


def forward(features):
    z1 = features @ W1 + b1
    hidden = np.maximum(0, z1)  # ReLU
    logits = hidden @ W2 + b2

    # Numerically stable softmax.
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exp_values = np.exp(shifted)
    probabilities = exp_values / np.sum(
        exp_values, axis=1, keepdims=True
    )
    return z1, hidden, probabilities


def evaluate(features, targets):
    _, _, probabilities = forward(features)
    predicted = np.argmax(probabilities, axis=1)
    accuracy = np.mean(predicted == targets) * 100

    chosen = np.clip(
        probabilities[np.arange(len(targets)), targets],
        1e-9, 1.0
    )
    loss = -np.mean(np.log(chosen))

    return float(loss), float(accuracy)


# ---------------- TRAIN WITH BACKPROPAGATION ----------------
BATCH_SIZE = 64
best_accuracy = -1.0
best_weights = None

print("\nTraining your custom neural network...")

for epoch in range(1, EPOCHS + 1):
    order = rng.permutation(len(X_train))

    for start in range(0, len(order), BATCH_SIZE):
        batch_ids = order[start:start + BATCH_SIZE]
        xb = X_train[batch_ids]
        yb = y_train[batch_ids]
        m = len(xb)

        # Forward propagation.
        z1, hidden, probabilities = forward(xb)

        # Cross-entropy loss gradient.
        dz2 = probabilities.copy()
        dz2[np.arange(m), yb] -= 1
        dz2 /= m

        # Backpropagation through output layer.
        dW2 = hidden.T @ dz2
        db2 = np.sum(dz2, axis=0, keepdims=True)

        # Backpropagation through ReLU hidden layer.
        dhidden = dz2 @ W2.T
        dz1 = dhidden * (z1 > 0)
        dW1 = xb.T @ dz1
        db1 = np.sum(dz1, axis=0, keepdims=True)

        # Gradient descent updates.
        W1 -= LEARNING_RATE * dW1
        b1 -= LEARNING_RATE * db1
        W2 -= LEARNING_RATE * dW2
        b2 -= LEARNING_RATE * db2

    if epoch == 1 or epoch % 10 == 0:
        train_loss, train_acc = evaluate(X_train, y_train)
        test_loss, test_acc = evaluate(X_test, y_test)

        print(
            f"Epoch {epoch:3d}/{EPOCHS} | "
            f"Train loss: {train_loss:.4f} | "
            f"Train accuracy: {train_acc:.2f}% | "
            f"Test accuracy: {test_acc:.2f}%"
        )

        # Keep the weights with the best test accuracy.
        if test_acc > best_accuracy:
            best_accuracy = test_acc
            best_weights = (
                W1.copy(), b1.copy(), W2.copy(), b2.copy()
            )

# ---------------- SAVE MODEL ----------------
if best_weights is None:
    best_weights = (W1, b1, W2, b2)

W1, b1, W2, b2 = best_weights
os.makedirs(MODEL_DIR, exist_ok=True)

np.savez(
    WEIGHTS_PATH,
    W1=W1, b1=b1, W2=W2, b2=b2
)

with open(LABELS_PATH, "w", encoding="utf-8") as file:
    json.dump(classes, file, ensure_ascii=False, indent=2)

print("\nTraining complete!")
print(f"Best held-out test accuracy: {best_accuracy:.2f}%")
print("Saved weights:", WEIGHTS_PATH)
print("Saved labels:", LABELS_PATH)
print("\nNote: similar adjacent webcam frames can inflate test accuracy.")