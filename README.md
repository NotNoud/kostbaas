# Vaste Lasten Tracker

Persoonlijke web-app om maandelijkse vaste lasten bij te houden. Het probleem: meerdere abonnementen worden op verschillende dagen afgeschreven, waardoor het onduidelijk is hoeveel er minimaal op de betaalrekening moet staan. Deze app maakt het overzichtelijk.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![Docker](https://img.shields.io/badge/Docker-Multi--arch-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Vaste lasten beheren** — invoeren met naam, bedrag (of % van inkomen) en afschrijfdag
- **Automatisch afvinken** — als de afschrijfdag al gepasseerd is, wordt de last automatisch als betaald gemarkeerd (handmatig overschrijfbaar)
- **Maandnavigatie** — elke maand is onafhankelijk, navigeer met pijltjes
- **Inkomen per maand** — berekent automatisch vrij besteedbaar bedrag
- **Percentage-lasten** — bijv. "Goede doelen = 5% van inkomen", herberekent bij inkomenwijziging
- **Scenario calculator** — voeg tijdelijke uitgaven toe om te zien wat er overblijft
- **Dark mode** — toggle in de header, onthoudt je voorkeur
- **Dashboard** — 4 overzichtskaarten: totaal lasten, vrij besteedbaar, al betaald, nog te betalen

## Screenshots

| Light mode | Dark mode |
|:---:|:---:|
| *komt nog* | *komt nog* |

## Snel starten

### Met Docker (aanbevolen)

Kopieer dit in een `docker-compose.yml` of plak het in Dockge. Werkt op AMD64 en ARM (Raspberry Pi).

```yaml
services:
  vaste-lasten:
    image: ghcr.io/notnoud/vaste-lasten:latest
    container_name: vaste-lasten
    ports:
      - "5000:5000"
    volumes:
      - ./vaste-lasten-data:/data
    restart: unless-stopped
    environment:
      - DEBUG=false
```

```bash
docker compose up -d
```

Open daarna http://localhost:5000

> **Updaten:** In Dockge klik je op **Update** om de nieuwste versie te pullen. Via CLI: `docker compose pull && docker compose up -d`

> **Data:** Je database wordt opgeslagen in `./vaste-lasten-data/expenses.db` en blijft behouden bij updates.

### Zonder Docker

```bash
git clone https://github.com/NotNoud/vaste-lasten.git
cd vaste-lasten
pip install -r requirements.txt
python app.py
```

## Tech stack

| Component | Technologie |
|---|---|
| Backend | Python 3.12 + Flask |
| Database | SQLite (via Docker volume) |
| Frontend | Tailwind CSS (CDN) + Vanilla JavaScript |
| Font | Inter (self-hosted) |
| Container | Docker, multi-arch (AMD64 + ARM) |

## Projectstructuur

```
vaste-lasten/
├── app.py                  # Flask backend + API routes + SQLite
├── templates/
│   └── index.html          # Single-page frontend (Tailwind + Vanilla JS)
├── static/
│   └── fonts/
│       └── Inter-Variable.woff2
├── requirements.txt        # flask==3.0.3
├── Dockerfile
├── docker-compose.yml
└── CLAUDE.md               # AI-context voor ontwikkeling
```

## API

| Methode | Route | Beschrijving |
|---|---|---|
| `GET` | `/` | Dashboard |
| `GET` | `/api/data?month=&year=` | Alle data als JSON |
| `POST` | `/api/income` | Inkomen opslaan |
| `POST` | `/api/expenses` | Vaste last toevoegen |
| `DELETE` | `/api/expenses/<id>` | Vaste last verwijderen |
| `POST` | `/api/expenses/<id>/toggle` | Betaalstatus togglen |

## Licentie

MIT
