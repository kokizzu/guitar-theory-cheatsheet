# Resume locally if GitHub Actions does not finish

From a terminal:

```bash
git clone https://github.com/kokizzu/guitar-theory-cheatsheet.git
cd guitar-theory-cheatsheet

cat .bootstrap/generator.b64.part* | base64 --decode > guitar_cheatsheet_generator.py
chmod +x guitar_cheatsheet_generator.py

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip svgwrite cairosvg

python guitar_cheatsheet_generator.py \
  --out-dir . \
  --stem guitar_theory_cheatsheet_programmatic

zip -9 guitar_cheatsheet_programmatic_bundle.zip \
  guitar_cheatsheet_generator.py \
  guitar_theory_cheatsheet_programmatic.svg \
  guitar_theory_cheatsheet_programmatic_1920x1080.png \
  guitar_theory_cheatsheet_programmatic_3840x2160.png

rm -rf .bootstrap
rm -f .github/workflows/bootstrap-assets.yml

git add -A
git commit -m "Add programmatic guitar theory cheatsheet outputs"
git push origin main
```

Expected committed files:

- `guitar_cheatsheet_generator.py`
- `guitar_theory_cheatsheet_programmatic.svg`
- `guitar_theory_cheatsheet_programmatic_1920x1080.png`
- `guitar_theory_cheatsheet_programmatic_3840x2160.png`
- `guitar_cheatsheet_programmatic_bundle.zip`

The generator draws the cheatsheet from structured music data, with string 1/high E on top and string 6/low E on the bottom.
