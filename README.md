# Installation steps

## Get files from github:
```
git clone https://github.com/hvdyinv4688hbv/bookly.git
```

## Set up virtual environment:
### Download python from
https://www.python.org/downloads/
### if you have a scarcity of [insert joke here later]
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

### If you need some books:
https://openlibrary.org/
https://archive.org/

#### bookly only accepts .pdf by the way
