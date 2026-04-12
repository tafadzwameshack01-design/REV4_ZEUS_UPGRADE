"""
ZEUS v4 — Central configuration and constants.
Target market: Over 2.5 Goals (>= 3 goals scored).
"""
import os
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

CAT_OFFSET = timedelta(hours=2)
WINDOW_HOURS = 6

_BUILTIN_KEY = "4d34b5f590msh5ce9ece8c1f6910p155a7ajsnfbaa5a5fb605"

def _load_api_key() -> str:
    """Load API key: Streamlit secrets → env var → built-in key."""
    try:
        import streamlit as st
        key = st.secrets.get("APIFOOTBALL_KEY", "")
        if key:
            return key
    except Exception:
        pass
    key = os.environ.get("APIFOOTBALL_KEY", "")
    if key:
        return key
    return _BUILTIN_KEY

APIFOOTBALL_KEY = _load_api_key()

HEADERS = {"User-Agent": "Mozilla/5.0 ZEUS-v4"}
HISTORY_GAMES = 25

FEATURE_DIM = 8
LEARNING_RATE = 0.008
LR_DECAY = 0.997
L2_REG = 0.002
WEIGHT_CLIP = 5.0
RANDOM_SEED = 42

SIM_MATCHES = 5000
SIM_MAX_ITER = 8

MIN_ACCURACY = 0.80
MIN_ROI = 0.0
MAX_DRAWDOWN_LIMIT = 0.22

INITIAL_BANKROLL = 1000.0
STAKE_FRACTION = 0.20
MIN_ODDS = 1.50
MAX_DAILY_EXPOSURE = 0.15
MAX_CONCURRENT = 5
LOSS_HALVE_STREAK = 2
LOSS_HALT_STREAK = 4

CONFIDENCE_THRESH = 0.78
TIER_ELITE = 90.0
TIER_STRONG = 83.0

OVER_LINE = 2.5

XG_TOTAL_MIN = 2.50
MIN_OVER25_RATE = 0.50
MIN_BTTS_RATE = 0.45
MIN_LEAGUE_AVG = 2.50
MAX_CLEAN_SHEET = 0.28
MIN_AVG_SCORED = 1.20

MIN_GAMES = 8
TOP_N = 8

LEAGUES = [
    ("eng.1", "Premier League", "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"),
    ("esp.1", "La Liga", "\U0001F1EA\U0001F1F8"),
    ("ger.1", "Bundesliga", "\U0001F1E9\U0001F1EA"),
    ("ita.1", "Serie A", "\U0001F1EE\U0001F1F9"),
    ("fra.1", "Ligue 1", "\U0001F1EB\U0001F1F7"),
    ("eng.2", "Championship", "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F"),
    ("esp.2", "La Liga 2", "\U0001F1EA\U0001F1F8"),
    ("ger.2", "2. Bundesliga", "\U0001F1E9\U0001F1EA"),
    ("ita.2", "Serie B", "\U0001F1EE\U0001F1F9"),
    ("fra.2", "Ligue 2", "\U0001F1EB\U0001F1F7"),
    ("ned.1", "Eredivisie", "\U0001F1F3\U0001F1F1"),
    ("por.1", "Primeira Liga", "\U0001F1F5\U0001F1F9"),
    ("bel.1", "Pro League", "\U0001F1E7\U0001F1EA"),
    ("sco.1", "Scottish Premiership", "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F"),
    ("tur.1", "Super Lig", "\U0001F1F9\U0001F1F7"),
    ("rus.1", "Russian Premier League", "\U0001F1F7\U0001F1FA"),
    ("aut.1", "Austrian Bundesliga", "\U0001F1E6\U0001F1F9"),
    ("gre.1", "Super League Greece", "\U0001F1EC\U0001F1F7"),
    ("cze.1", "Czech First League", "\U0001F1E8\U0001F1FF"),
    ("pol.1", "Ekstraklasa", "\U0001F1F5\U0001F1F1"),
    ("den.1", "Superliga", "\U0001F1E9\U0001F1F0"),
    ("swe.1", "Allsvenskan", "\U0001F1F8\U0001F1EA"),
    ("nor.1", "Eliteserien", "\U0001F1F3\U0001F1F4"),
    ("sui.1", "Super League", "\U0001F1E8\U0001F1ED"),
    ("ukr.1", "Ukrainian Premier", "\U0001F1FA\U0001F1E6"),
    ("srb.1", "SuperLiga Serbia", "\U0001F1F7\U0001F1F8"),
    ("cro.1", "HNL", "\U0001F1ED\U0001F1F7"),
    ("usa.1", "MLS", "\U0001F1FA\U0001F1F8"),
    ("bra.1", "Brasileirao", "\U0001F1E7\U0001F1F7"),
    ("arg.1", "Liga Profesional", "\U0001F1E6\U0001F1F7"),
    ("mex.1", "Liga MX", "\U0001F1F2\U0001F1FD"),
    ("col.1", "Liga BetPlay", "\U0001F1E8\U0001F1F4"),
    ("chi.1", "Primera Division", "\U0001F1E8\U0001F1F1"),
    ("ecu.1", "LigaPro", "\U0001F1EA\U0001F1E8"),
    ("per.1", "Liga 1", "\U0001F1F5\U0001F1EA"),
    ("uru.1", "Primera Division", "\U0001F1FA\U0001F1FE"),
    ("ven.1", "Primera Division", "\U0001F1FB\U0001F1EA"),
    ("bol.1", "Division Profesional", "\U0001F1E7\U0001F1F4"),
    ("jpn.1", "J1 League", "\U0001F1EF\U0001F1F5"),
    ("kor.1", "K League 1", "\U0001F1F0\U0001F1F7"),
    ("chn.1", "Chinese Super League", "\U0001F1E8\U0001F1F3"),
    ("aus.1", "A-League", "\U0001F1E6\U0001F1FA"),
    ("ind.1", "ISL", "\U0001F1EE\U0001F1F3"),
    ("sau.1", "Saudi Pro League", "\U0001F1F8\U0001F1E6"),
    ("egy.1", "Egyptian Premier", "\U0001F1EA\U0001F1EC"),
    ("mar.1", "Botola Pro", "\U0001F1F2\U0001F1E6"),
    ("rsa.1", "DStv Premiership", "\U0001F1FF\U0001F1E6"),
    ("nig.1", "NPFL", "\U0001F1F3\U0001F1EC"),
    ("uefa.champions", "UEFA Champions League", "\U0001F3C6"),
    ("uefa.europa", "UEFA Europa League", "\U0001F948"),
    ("conmebol.libertadores", "Copa Libertadores", "\U0001F3C6"),
]

LEAGUE_GOAL_AVG = {
    "eng.1": 2.85, "esp.1": 2.55, "ger.1": 3.05, "ita.1": 2.65, "fra.1": 2.60,
    "eng.2": 2.75, "esp.2": 2.40, "ger.2": 2.80, "ita.2": 2.50, "fra.2": 2.45,
    "ned.1": 3.10, "por.1": 2.70, "bel.1": 2.90, "sco.1": 2.75, "tur.1": 2.80,
    "rus.1": 2.50, "aut.1": 2.95, "gre.1": 2.60, "cze.1": 2.70, "pol.1": 2.60,
    "den.1": 3.00, "swe.1": 2.80, "nor.1": 2.90, "sui.1": 2.85, "ukr.1": 2.45,
    "srb.1": 2.55, "cro.1": 2.70,
    "usa.1": 2.90, "bra.1": 2.55, "arg.1": 2.40, "mex.1": 2.65, "col.1": 2.50,
    "chi.1": 2.45, "ecu.1": 2.55, "per.1": 2.40, "uru.1": 2.50, "ven.1": 2.35,
    "bol.1": 2.30,
    "jpn.1": 2.65, "kor.1": 2.60, "chn.1": 2.55, "aus.1": 2.80, "ind.1": 2.50,
    "sau.1": 2.70,
    "egy.1": 2.40, "mar.1": 2.30, "rsa.1": 2.45, "nig.1": 2.35,
    "uefa.champions": 2.95, "uefa.europa": 2.80, "conmebol.libertadores": 2.60,
}

REGION_EUROPE = {
    "eng", "esp", "ger", "ita", "fra", "ned", "por", "bel", "sco", "tur",
    "rus", "aut", "gre", "cze", "pol", "den", "swe", "nor", "sui", "ukr", "srb", "cro",
}
REGION_AMERICAS = {"usa", "bra", "arg", "mex", "col", "chi", "ecu", "per", "uru", "ven", "bol"}
REGION_ASIA = {"jpn", "kor", "chn", "aus", "ind", "sau"}
REGION_MENA = {"egy", "mar", "rsa", "nig"}
REGION_CUPS = {"uefa", "conmebol"}
