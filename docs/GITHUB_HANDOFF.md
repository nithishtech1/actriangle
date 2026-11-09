# Person 3 repository handoff

This implementation extends `nithishtech1/actriangle`, scaffold commit `cd3a074`, on branch
`feat/person3-software`. The original folder layout, eight CSV columns, phases, sensor mapping,
offset convention, shared configuration and `.env` secret handling are retained. Firmware is unchanged.

The source ZIP contains the complete project without `.git`, credentials, virtual environments or caches.
The accompanying `ClimaTwin-person3.patch` contains the changes relative to the original scaffold, including
the FAKE replay CSVs. Sample PDF/analysis outputs are delivered separately and are not included in the patch.

Once the implementation branch is published, teammates can retrieve it without copying files:

```powershell
git fetch origin
git switch --track origin/feat/person3-software
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m streamlit run app/dashboard.py
```

If using the offline patch instead, apply it in a clean checkout of the original scaffold:

```powershell
git status
git switch -c feat/person3-software
# Replace the path below with where you saved the supplied patch.
git apply --check C:\path\to\ClimaTwin-person3.patch
git apply C:\path\to\ClimaTwin-person3.patch
python -m pip install -r requirements-dev.txt
python -m pytest -q
git add .
git commit -m "Implement Person 3 ClimaTwin software pipeline"
git push -u origin feat/person3-software
```

Use a clean checkout, review `git status` before staging, and open a pull request for the team.
If `git apply --check` reports conflicts because teammates changed the scaffold, resolve those differences
before applying; do not force an overwrite. Never commit `.env` or bot credentials.
