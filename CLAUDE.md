# Kostbaas

Persoonlijke web-app om maandelijkse vaste lasten bij te houden. Het probleem dat dit oplost: meerdere abonnementen worden op verschillende dagen afgeschreven, waardoor het onduidelijk is hoeveel er minimaal op de betaalrekening moet staan. De app maakt het mogelijk om per maand lasten af te vinken en toont altijd het actuele overzicht.

## Wat de app doet

- Vaste lasten invoeren met naam, bedrag (of % van inkomen) en dag van de maand
- Automatisch afvinken: als de afschrijfdag al gepasseerd is vandaag, wordt de last automatisch als betaald gemarkeerd (met "auto" badge, handmatig overschrijfbaar)
- Voorbije maanden: alle lasten met vaste dag worden automatisch als betaald gemarkeerd
- Per maand bijhouden: elke maand is onafhankelijk, maandnavigatie via pijltjes
- Inkomen invoeren per maand → berekent automatisch vrij besteedbaar
- Inkomen overnemen: als inkomen 0 is, kan je met → knop het inkomen van vorige maand overnemen
- Percentage-lasten: bijv. "Goede doelen = 5% van inkomen" → bedrag herberekent bij inkomenwijziging
- Actieve periodes: per expense instelbaar wanneer deze actief is (bijv. jan 2025 – dec 2026, of doorlopend)
- Inactief per maand: individuele expenses kunnen per maand inactief gezet worden (tellen niet mee in totalen)
- Scenario calculator: voeg tijdelijke uitgaven toe om te zien wat er overblijft
- Dashboard met 4 cards: totaal lasten / al betaald / nog te betalen / vrij besteedbaar
- Tabbladen: Overzicht (huidige view) + Tijdlijn (staafgrafiek inkomen vs lasten per maand)

## Tech stack

- **Backend**: Python 3.12 + Flask (app.py)
- **Database**: SQLite via Docker volume (`./data/expenses.db`)
- **Frontend**: Tailwind CSS CDN + Vanilla JavaScript (geen build step)
- **Container**: Docker + docker-compose (multi-arch: werkt op AMD64 en Raspberry Pi ARM)

## Bestandsstructuur

```
kostbaas/
├── app.py                  # Flask backend + alle API routes + SQLite logica
├── templates/
│   └── index.html          # Single-page frontend (Tailwind + Vanilla JS, AJAX)
├── requirements.txt        # Alleen: flask==3.0.3
├── Dockerfile              # python:3.12-slim, EXPOSE 5000
├── docker-compose.yml      # port 5000:5000, volume ./data:/data
├── .gitignore              # data/, __pycache__, *.pyc
└── CLAUDE.md               # dit bestand
```

## Database schema (SQLite)

```sql
CREATE TABLE expenses (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               TEXT    NOT NULL,
    amount             REAL,             -- NULL als percentage-gebaseerd
    percentage         REAL,             -- NULL als vast bedrag
    day_of_month       INTEGER DEFAULT 1,
    active_from_month  INTEGER DEFAULT NULL,  -- NULL = altijd actief
    active_from_year   INTEGER DEFAULT NULL,
    active_until_month INTEGER DEFAULT NULL,  -- NULL = doorlopend
    active_until_year  INTEGER DEFAULT NULL
);

CREATE TABLE monthly_payments (
    expense_id  INTEGER,
    month       INTEGER,
    year        INTEGER,
    paid        INTEGER DEFAULT 0,
    overridden  INTEGER DEFAULT 0,  -- 1 = gebruiker heeft handmatig overschreven
    inactive    INTEGER DEFAULT 0,  -- 1 = inactief deze maand, telt niet mee in totalen
    PRIMARY KEY (expense_id, month, year),
    FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE
);

CREATE TABLE monthly_income (
    month   INTEGER,
    year    INTEGER,
    amount  REAL DEFAULT 0,
    PRIMARY KEY (month, year)
);
```

## API routes

| Method | Route | Wat het doet |
|--------|-------|--------------|
| GET | `/` | Render dashboard |
| GET | `/api/data?month=&year=` | Alle data als JSON (expenses + summary + suggested_income) |
| POST | `/api/income` | Inkomen opslaan voor maand/jaar |
| POST | `/api/expenses` | Nieuwe vaste last toevoegen (incl. active_from/active_until) |
| PUT | `/api/expenses/<id>` | Vaste last bijwerken (incl. active_from/active_until) |
| DELETE | `/api/expenses/<id>` | Vaste last verwijderen (cascade payments) |
| POST | `/api/expenses/<id>/toggle` | Betaald-status togglen voor maand/jaar |
| POST | `/api/expenses/<id>/toggle-inactive` | Inactief-status togglen voor maand/jaar |
| GET | `/api/yearly?year=` | Per maand: income, total_expenses, disposable (voor tijdlijn) |

## Auto-afvinken logica

Prioriteit bij bepalen van betaald-status:
1. Als `overridden = 1` in DB → gebruik `paid` uit DB (handmatig gezet door gebruiker)
2. Als voorbije maand EN `day_of_month` is niet NULL → automatisch betaald (`auto = True`)
3. Als huidige maand EN `day_of_month <= vandaag.dag` → automatisch betaald (`auto = True`)
4. Toekomstige maanden → niet automatisch betaald
5. `day_of_month = NULL` (handmatig) → nooit auto-afvinken

Toggle-gedrag:
- Klik op auto-betaald item → markeert als niet betaald (`overridden=1, paid=0`)
- Klik op niet-betaald item → markeert als betaald (`overridden=1, paid=1`)
- Daarna: gewoon toggle op `paid`, `overridden` blijft `1`

## DB-pad detectie (in app.py)

```python
def get_db_path():
    if os.path.isdir('/data'):
        return '/data/expenses.db'   # Docker
    os.makedirs('data', exist_ok=True)
    return 'data/expenses.db'        # Lokaal
```

## Frontend secties (index.html)

1. **Header**: app-naam links, maandnavigatie midden (`‹ Maart 2026 ›`), dark mode toggle rechts
2. **Tabbladen**: Overzicht | Tijdlijn — actieve tab indigo, inactieve tab subtle
3. **Tab Overzicht**:
   - **Inkomen card**: groot invoerveld `€ ____`, opslaan bij `onblur`, → knop voor overnemen vorige maand
   - **4 summary cards** (2×2 grid): indigo/groen/oranje/paars — paars wordt rood bij negatief saldo
   - **Vaste lasten lijst**: checkbox + naam + badges (auto/overschreven/handmatig/inactief) + bedrag + edit/verwijder, gesorteerd op dag. Inactieve rijen krijgen `opacity-40`
   - **Toevoegen/bewerk formulier**: uitklapbaar, velden: naam / type (vast of %) / dag / bedrag of % / actief vanaf / actief tot / inactief deze maand (alleen edit)
   - **Scenario calculator**: tijdelijke uitgaven toevoegen, toont effect op vrij besteedbaar
4. **Tab Tijdlijn**: Canvas staafgrafiek met inkomen (indigo) vs lasten (amber) per maand. Hover toont bedrag, klik navigeert naar die maand

## Starten

```bash
# Met Docker (aanbevolen, ook voor Raspberry Pi)
docker compose up -d
# Open: http://localhost:5000

# Zonder Docker
pip install flask
python app.py
# Open: http://localhost:5000
```

## Belangrijk bij aanpassingen

- Alle data staat in `./data/expenses.db` — dit bestand niet verwijderen
- Percentage-lasten herberekenen automatisch als inkomen wijzigt (server-side bij elke `/api/data` call)
- De frontend gebruikt alleen Vanilla JS + AJAX, geen frameworks of build tools
- Tailwind via CDN (play-modus), dus dynamisch toegevoegde klassen werken direct
- Docker volume `./data:/data` zorgt voor persistentie bij container-restarts
