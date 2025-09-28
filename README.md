# Installation steps

## Get files from github:
```
git clone https://github.com/hvdyinv4688hbv/bookly.git
```

## Set up virtual environment:
```
cd bookly
python3 -m venv .venv
```

```
source .venv/bin/activate   # Linux/macOS
```
## or
```
.venv\Scripts\activate      # Windows (PowerShell)
```

## Install dependencies:
```
pip install -r requirements.txt
spacy download en_core_web_sm
```

# Run the bookly program
```
python bookly.py
```
