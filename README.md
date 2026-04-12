# ZEUS v4 — Neural Football Intelligence System

Over 2.5 Goals prediction engine powered by Poisson modeling, machine learning, and Kelly Criterion staking.

## Features

- **51 League Coverage** — Europe, Americas, Asia/Pacific, Middle East/Africa, and continental cups
- **Dual-Model Ensemble** — Poisson probability (65%) + logistic regression ML (35%)
- **7-Factor Confidence Scoring** — Ensemble probability, historical Over-2.5 rate, BTTS rate, recent form, clean-sheet penalty, variance stability, and H2H boost
- **6-Gate Hard Filter** — xG total, Over-2.5 rate, BTTS rate, league avg goals, clean-sheet rate, avg scored
- **Kelly Criterion Staking** — Fractional Kelly with risk controls (max exposure, concurrent bet limits, loss streak handling)
- **Self-Repair Simulation** — 5,000 synthetic matches per iteration, up to 8 auto-fix cycles
- **Online Learning** — Model weights update after each graded result
- **SQLite Persistence** — Predictions, results, bankroll history, and model state

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your API key
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your RapidAPI key

# Run the application
streamlit run app.py
```

## Configuration

All parameters are centralized in `data/constants.py`:

- **Confidence threshold**: 78% (configurable via UI slider)
- **Tier classification**: Elite (>=90%), Strong (83-89%), Confident (78-82%)
- **Betting controls**: Max 5 concurrent bets, 15% max daily exposure, 1.50 minimum odds
- **Loss protection**: Stake halved after 2 consecutive losses, betting halted after 4

## Architecture

```
ZEUS_V4/
├── app.py                  # Streamlit UI entry point
├── data/
│   └── constants.py        # Central configuration
├── models/
│   ├── poisson_model.py    # Poisson probability calculations
│   ├── ml_model.py         # Logistic regression with online learning
│   └── ensemble.py         # Combined prediction + confidence scoring
├── services/
│   ├── apifootball.py      # API-Football v3 data fetching
│   ├── stats_engine.py     # Per-team statistical analysis
│   ├── betting_engine.py   # Kelly Criterion staking
│   └── scanner.py          # Multi-league scanning pipeline
├── database/
│   └── db.py               # SQLite persistence layer
├── simulation/
│   └── sim_engine.py       # Self-repair simulation engine
└── utils/
    └── helpers.py           # Time, scoring, and utility functions
```

## API Requirements

This application requires an API-Football v3 key from RapidAPI. Add it to `.streamlit/secrets.toml`:

```toml
APIFOOTBALL_KEY = "your_rapidapi_key_here"
```

## License

MIT
