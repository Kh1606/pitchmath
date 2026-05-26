"""
UI Style Constants and CSS Injection for MetaRen Analytics
"""

import streamlit as st

# =============================================================================
# COLOR CONSTANTS
# =============================================================================

COLOR_WIN = "#4CAF50"
COLOR_DRAW = "#FFC107"
COLOR_LOSE = "#F44336"
COLOR_PRIMARY = "#6366F1"
COLOR_TEXT = "#E5E7EB"
COLOR_TEXT_MUTED = "#8B9DC3"
COLOR_BG_CARD = "#1E2235"
COLOR_BG_DARK = "#161927"
COLOR_BORDER = "#2D3548"

# Team Colors
TEAM_COLORS = {
    "Barcelona": "#A50044",
    "Real Madrid": "#FEBE10",
    "Liverpool": "#C8102E",
    "Manchester City": "#6CABDD",
    "Manchester United": "#DA291C",
    "Arsenal": "#EF0107",
    "Chelsea": "#034694",
    "Bayern": "#DC052D",
    "Juventus": "#000000",
    "PSG": "#004170",
    "default": "#6366F1"
}

# Result colors mapping
RESULT_COLORS = {
    "Win": COLOR_WIN,
    "Draw": COLOR_DRAW,
    "Loss": COLOR_LOSE
}


def get_team_color(team_name: str) -> str:
    """Get team color, with fallback to default."""
    for key, color in TEAM_COLORS.items():
        if key.lower() in team_name.lower():
            return color
    return TEAM_COLORS["default"]


# =============================================================================
# LEAGUE CONFIGURATIONS
# =============================================================================

TOP_5_LEAGUES = {
    "EPL": "Premier League",
    "La Liga": "La Liga",
    "Serie A": "Serie A",
    "Bundesliga": "Bundesliga",
    "Ligue 1": "Ligue 1"
}

LEAGUE_DISPLAY_NAMES = {
    "All Leagues": None,
    "Premier League (EPL)": "Premier League",
    "La Liga": "La Liga",
    "Serie A": "Serie A",
    "Bundesliga": "Bundesliga",
    "Ligue 1": "Ligue 1",
    "FA Cup": "FA Cup",
    "EFL Cup": "League Cup",
    "Copa del Rey": "Copa del Rey",
    "Coppa Italia": "Coppa Italia",
    "DFB Pokal": "DFB Pokal",
    "UCL": "UEFA Champions League",
    "Europa League": "UEFA Europa League",
    "Conference League": "UEFA Conference League",
}

# Stat type mappings
STAT_TYPES = {
    "Goals": "goals",
    "Corners": "Corner Kicks",
    "Cards": "Yellow Cards"
}


# =============================================================================
# CSS INJECTION
# =============================================================================

def inject_custom_css():
    """Inject custom CSS for professional Flashscore-style dashboard."""
    st.markdown("""
    <style>
        /* Global Styling */
        .main {
            background-color: #0E1117;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        }
        
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stCheckbox label,
        [data-testid="stSidebar"] .stRadio label {
            color: #E5E7EB !important;
        }
        
        /* Header Styling */
        .dashboard-header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            border-left: 4px solid #6366F1;
        }
        
        .dashboard-header h1 {
            color: #FFFFFF;
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0;
        }
        
        .dashboard-header p {
            color: #8B8B8B;
            font-size: 0.95rem;
            margin-top: 0.5rem;
        }
        
        /* Match Header Card */
        .match-header-card {
            background: linear-gradient(145deg, #1E2235 0%, #161927 100%);
            border-radius: 16px;
            padding: 2rem;
            border: 1px solid #2D3548;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        
        .match-header-teams {
            font-size: 1.8rem;
            font-weight: 700;
            color: #FFFFFF;
            margin: 1rem 0;
        }
        
        .match-header-score {
            font-size: 3rem;
            font-weight: 800;
            color: #6366F1;
            margin: 0.5rem 0;
        }
        
        .match-header-ht {
            font-size: 1rem;
            color: #8B9DC3;
        }
        
        .match-header-meta {
            font-size: 0.85rem;
            color: #6B7280;
            margin-top: 0.5rem;
        }
        
        /* Metric Cards */
        .metric-card {
            background: linear-gradient(145deg, #1E2235 0%, #161927 100%);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid #2D3548;
            transition: transform 0.2s, box-shadow 0.2s;
            text-align: center;
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        }
        
        .metric-value {
            font-size: 2.2rem;
            font-weight: 700;
            color: #FFFFFF;
            line-height: 1;
        }
        
        .metric-label {
            font-size: 0.8rem;
            color: #8B9DC3;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 0.5rem;
        }
        
        /* Hit Rate Card */
        .hitrate-card {
            background: linear-gradient(145deg, #1E2235 0%, #161927 100%);
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid #2D3548;
            text-align: center;
            margin: 0.5rem 0;
        }
        
        .hitrate-value {
            font-size: 1.8rem;
            font-weight: 700;
            line-height: 1;
        }
        
        .hitrate-label {
            font-size: 0.75rem;
            color: #8B9DC3;
            margin-top: 0.25rem;
        }
        
        .hitrate-pct {
            font-size: 1rem;
            font-weight: 600;
            margin-top: 0.25rem;
        }
        
        /* Empty State Card */
        .empty-state {
            background: linear-gradient(145deg, #1E2235 0%, #161927 100%);
            border-radius: 12px;
            padding: 2rem;
            border: 1px solid #2D3548;
            text-align: center;
            color: #8B9DC3;
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        /* Match Card Styling */
        .match-card {
            background: linear-gradient(145deg, #1E2235 0%, #1A1D2E 100%);
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 0.75rem;
            border: 1px solid #2D3548;
            transition: all 0.2s;
        }
        
        .match-card:hover {
            border-color: #4A5568;
            transform: translateX(4px);
        }
        
        .match-date {
            font-size: 0.75rem;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .match-teams {
            font-size: 1.1rem;
            font-weight: 600;
            color: #E5E7EB;
            margin: 0.5rem 0;
        }
        
        .match-score {
            font-size: 1.3rem;
            font-weight: 700;
            color: #FFFFFF;
        }
        
        .match-league {
            display: inline-block;
            font-size: 0.7rem;
            padding: 0.25rem 0.6rem;
            border-radius: 4px;
            font-weight: 600;
            text-transform: uppercase;
            background-color: #4A5568;
            color: white;
        }
        
        /* Win/Loss Indicators */
        .result-win { color: #4CAF50; }
        .result-draw { color: #FFC107; }
        .result-loss { color: #F44336; }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: #1E2235;
            border-radius: 8px;
            padding: 10px 20px;
            color: #8B9DC3;
            border: 1px solid #2D3548;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #6366F1 !important;
            color: white !important;
            border-color: #6366F1 !important;
        }
        
        /* Section Headers */
        .section-header {
            color: #E5E7EB;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #2D3548;
        }
        
        /* Widget Title */
        .widget-title {
            color: #E5E7EB;
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        /* Sidebar Panel */
        .sidebar-panel {
            background: linear-gradient(145deg, #1E2235 0%, #161927 100%);
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid #2D3548;
        }
        
        .sidebar-panel-title {
            color: #E5E7EB;
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .sidebar-panel-content {
            color: #8B9DC3;
            font-size: 0.85rem;
        }
        
        /* DNA Radar Chart Container */
        .dna-container {
            background: linear-gradient(145deg, #1E2235 0%, #161927 100%);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid #2D3548;
        }
        
        /* Percentile Row for Team DNA */
        .percentile-row {
            display: flex;
            align-items: center;
            margin-bottom: 0.75rem;
            padding: 0.5rem;
            background: rgba(30, 34, 53, 0.5);
            border-radius: 6px;
        }
        
        .percentile-label {
            flex: 0 0 120px;
            color: #E5E7EB;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .percentile-bar-bg {
            flex: 1;
            height: 8px;
            background: #2D3548;
            border-radius: 4px;
            margin: 0 12px;
            overflow: hidden;
        }
        
        .percentile-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .percentile-value {
            flex: 0 0 50px;
            color: #FFFFFF;
            font-size: 0.9rem;
            font-weight: 600;
            text-align: right;
        }
        
        /* Hide default streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Insight Box */
        .insight-box {
            background: linear-gradient(135deg, #1a472a 0%, #0d2818 100%);
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            border-left: 4px solid #4CAF50;
        }
        
        .insight-box-warning {
            background: linear-gradient(135deg, #4a3728 0%, #2d1f14 100%);
            border-left-color: #FFC107;
        }
    </style>
    """, unsafe_allow_html=True)
