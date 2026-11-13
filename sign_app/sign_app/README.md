# Sign Language Translator (webcam -> words -> sentence)

## Setup (VS Code terminal, Python 3.9-3.11 recommended)
    python -m venv venv
    venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt

## Steps
1. Collect data, once per sign (press R to record, Q to quit):
       python collect_data.py HELLO
       python collect_data.py THANKS
       python collect_data.py I
       python collect_data.py WATER
       python collect_data.py WANT
   Use 4-6+ signs, vary hand distance/angle a bit while recording.
2. Train:   python train.py
3. Run:     python app.py
   Hold a sign ~0.5 s to add a word. C clear, B backspace, S speak, Q quit.

## Structure
sign_app/
  collect_data.py   record landmarks from webcam
  train.py          train classifier
  app.py            live recognition + sentence + speech
  utils.py          landmark normalization
  data/dataset.csv  created by collect_data.py
  models/sign_model.pkl  created by train.py
