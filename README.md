# 🧬 GA Warehouse Optimizer
Streamlit app solving a two-echelon capacitated warehouse location problem with a Genetic Algorithm.

## Run locally
```bash
pip install -r requirements.txt
python make_template.py      # (re)creates input_template.xlsx
streamlit run app.py
```
## Deploy
GitHub Pages only hosts static files and cannot run Python. Push this folder to GitHub, then deploy it free on
[Streamlit Community Cloud](https://share.streamlit.io) (New app → pick repo → `app.py`). You get a public URL.

## Files
`app.py` UI · `ga_solver.py` GA + LP routing · `make_template.py` Excel template generator · `input_template.xlsx`
