"""
Match Analyzer Component for PitchMath Analytics
Head-to-head analysis with form-line engine.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional, Dict

from ui_style import get_team_color, COLOR_WIN, COLOR_LOSE
from data_access import (
    filter_matches_by_team, 
    get_head_to_head_matches,
    get_available_teams
)
from logic.stat_engine import compute_stat_per_match, generate_chart_key
from components.charts import render_line_visualization, render_hit_rate_cards


def render_match_analyzer_sidebar(df_matches: pd.DataFrame, available_teams: list,
                                   nav_home: Optional[str] = None,
                                   nav_away: Optional[str] = None) -> dict:
    """Render Match Analyzer specific sidebar options.
    
    nav_home / nav_away: preselected teams from fixture click-through navigation.
    """
    st.sidebar.markdown("### ⚔️ Match Selection")
    
    if not available_teams:
        st.sidebar.warning("No teams available for selected competition.")
        return {"home_team": None, "away_team": None, "selected_match": None}
    
    # Determine default home team index
    home_default_idx = 0
    if nav_home and nav_home in available_teams:
        home_default_idx = available_teams.index(nav_home)
    
    home_team = st.sidebar.selectbox(
        "Home Team",
        available_teams,
        index=home_default_idx,
        key="match_home_team"
    )
    
    away_options = [t for t in available_teams if t != home_team]
    if not away_options:
        st.sidebar.warning("Only one team available.")
        return {"home_team": home_team, "away_team": None, "selected_match": None}
    
    # Determine default away team index
    away_default_idx = 0
    if nav_away and nav_away in away_options:
        away_default_idx = away_options.index(nav_away)
    
    away_team = st.sidebar.selectbox(
        "Away Team",
        away_options,
        index=away_default_idx,
        key="match_away_team"
    )
    
    # Check for head-to-head matches
    h2h_matches = get_head_to_head_matches(df_matches, home_team, away_team)
    
    selected_match = None
    if len(h2h_matches) > 0:
        st.sidebar.markdown("#### 📜 Past Meetings")
        match_options = []
        for _, row in h2h_matches.iterrows():
            try:
                date_str = datetime.strptime(str(row['date'])[:10], '%Y-%m-%d').strftime('%b %d, %Y')
            except:
                date_str = str(row['date'])[:10]
            match_str = f"{date_str} | {row['home_team']} {row['home_score']}-{row['away_score']} {row['away_team']}"
            match_options.append((row['game_id'], match_str))
        
        match_labels = [m[1] for m in match_options]
        selected_idx = st.sidebar.selectbox(
            "Select Match",
            range(len(match_labels)),
            format_func=lambda x: match_labels[x],
            key="h2h_match_selector"
        )
        selected_match = h2h_matches.iloc[selected_idx].to_dict()
    else:
        st.sidebar.markdown("""
        <div class="sidebar-panel">
            <div class="sidebar-panel-content">
                📭 No past meetings found between these teams. 
                Analysis will use team form data.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    return {
        "home_team": home_team,
        "away_team": away_team,
        "selected_match": selected_match,
        "h2h_matches": h2h_matches
    }


def render_match_header(match: Optional[dict], home_team: str, away_team: str):
    """Render match header card."""
    
    if match:
        try:
            date_str = datetime.strptime(str(match['date'])[:10], '%Y-%m-%d').strftime('%B %d, %Y')
        except:
            date_str = str(match['date'])[:10]
        
        ft_score = f"{match['home_score']} - {match['away_score']}"
        ht_score = f"HT: {match['home_score_ht']} - {match['away_score_ht']}"
        league = match.get('league_name', 'Unknown')
        
        st.markdown(f"""
        <div class="match-header-card">
            <div class="match-header-meta">
                <span class="match-league">{league}</span> • {date_str}
            </div>
            <div class="match-header-teams">{match['home_team']} vs {match['away_team']}</div>
            <div class="match-header-score">{ft_score}</div>
            <div class="match-header-ht">{ht_score}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="match-header-card">
            <div class="match-header-meta">📊 Form Analysis Mode</div>
            <div class="match-header-teams">{home_team} vs {away_team}</div>
            <div class="match-header-ht">No past meetings - analyzing team form</div>
        </div>
        """, unsafe_allow_html=True)


def render_match_analyzer_main(selections: dict, df_matches: pd.DataFrame, 
                                df_team_stats: pd.DataFrame):
    """Render main Match Analyzer page."""
    

    
    home_team = selections.get("home_team")
    away_team = selections.get("away_team")
    selected_match = selections.get("selected_match")
    
    if not home_team or not away_team:
        st.warning("Please select both teams in the sidebar.")
        return
    
    # Match header
    render_match_header(selected_match, home_team, away_team)
    
    # Period tabs
    period_tab1, period_tab2, period_tab3, period_tab4 = st.tabs(
        ["📊 Full Match", "1️⃣ 1st Half", "2️⃣ 2nd Half", "⭐ Specials"]
    )
    
    with period_tab1:
        # Full Match: Goals, Corners, Cards
        render_betting_analysis(df_matches, df_team_stats, home_team, away_team, "Full",
                                include_corners=True)
    
    with period_tab2:
        # 1st Half: Goals, Cards only (no corners — unreliable)
        render_betting_analysis(df_matches, df_team_stats, home_team, away_team, "1st Half",
                                include_corners=False)
    
    with period_tab3:
        # 2nd Half: Goals, Cards only (no corners — derived from unreliable 1H)
        render_betting_analysis(df_matches, df_team_stats, home_team, away_team, "2nd Half",
                                include_corners=False)
    
    with period_tab4:
        render_specials_analysis(df_matches, home_team, away_team)


def render_betting_analysis(df_matches: pd.DataFrame, df_team_stats: pd.DataFrame,
                            home_team: str, away_team: str, period: str,
                            include_corners: bool = True):
    """Render form-line analysis for a specific period."""
    
    if include_corners:
        # Full match: Goals, Corners, Cards
        market_tab1, market_tab2, market_tab3 = st.tabs(["⚽ Goals", "🚩 Corners", "🟨 Cards"])
        
        with market_tab1:
            render_market_analysis(df_matches, df_team_stats, home_team, away_team, 
                                   "Goals", period)
        with market_tab2:
            render_market_analysis(df_matches, df_team_stats, home_team, away_team, 
                                   "Corners", period)
        with market_tab3:
            render_market_analysis(df_matches, df_team_stats, home_team, away_team, 
                                   "Cards", period)
    else:
        # 1H / 2H: Goals, Cards only (no corners)
        market_tab1, market_tab2 = st.tabs(["⚽ Goals", "🟨 Cards"])
        
        with market_tab1:
            render_market_analysis(df_matches, df_team_stats, home_team, away_team, 
                                   "Goals", period)
        with market_tab2:
            render_market_analysis(df_matches, df_team_stats, home_team, away_team, 
                                   "Cards", period)


def render_market_analysis(df_matches: pd.DataFrame, df_team_stats: pd.DataFrame,
                           home_team: str, away_team: str, market: str, period: str):
    """Render analysis for a specific market and period."""
    
    # Create unique key prefix for this context
    key_prefix = f"match_{period}_{market}"
    
    # Perspective toggle
    perspective = st.radio(
        "Perspective",
        ["Total Match", "Team Only"],
        index=0,
        horizontal=True,
        key=f"{key_prefix}_perspective",
        help="Total Match: combined stats from both teams. Team Only: each team's own stat."
    )
    
    # Line selector
    if market == "Goals":
        lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        default_line = 2.5
    elif market == "Corners":
        lines = [5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5]
        default_line = 9.5
    else:  # Cards
        lines = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5]
        default_line = 3.5
    
    col1, col2 = st.columns([1, 1])
    with col1:
        line = st.select_slider(
            f"Select {market} Line",
            options=lines,
            value=default_line,
            key=f"{key_prefix}_line"
        )
    with col2:
        direction = st.radio(
            "Direction",
            ["Over", "Under"],
            index=0,
            horizontal=True,
            key=f"{key_prefix}_direction"
        )
    
    st.markdown("---")
    
    # Compute stats for each team
    df_stats_home = compute_stat_per_match(
        df_matches, df_team_stats, home_team, 
        market, period, venue="Home", perspective=perspective
    )
    df_stats_away = compute_stat_per_match(
        df_matches, df_team_stats, away_team, 
        market, period, venue="Away", perspective=perspective
    )
    
    # Render visualizations
    home_color = get_team_color(home_team)
    away_color = get_team_color(away_team)
    
    # Generate unique chart keys
    home_chart_key = generate_chart_key("match", period, market, direction, line, home_team, perspective)
    away_chart_key = generate_chart_key("match", period, market, direction, line, away_team, perspective)
    
    perspective_label = "" if perspective == "Total Match" else " (Team Stats Only)"
    
    st.markdown(f"### {home_team} (HOME matches only){perspective_label}")
    hits_home, total_home = render_line_visualization(
        df_stats_home, home_team, line, direction, home_color,
        f"{home_team} - {market} per match",
        home_chart_key
    )
    
    st.markdown(f"### {away_team} (AWAY matches only){perspective_label}")
    hits_away, total_away = render_line_visualization(
        df_stats_away, away_team, line, direction, away_color,
        f"{away_team} - {market} per match",
        away_chart_key
    )
    
    st.markdown("---")
    st.markdown("### 📈 Hit Rate Summary")
    render_hit_rate_cards(hits_home, total_home, hits_away, total_away,
                          home_team, away_team, direction, line)


def render_specials_analysis(df_matches: pd.DataFrame, home_team: str, away_team: str):
    """Render extra-stats analysis (BTTS, Draw at least one half)."""
    
    st.markdown("### ⭐ Special Markets")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### BTTS (Both Teams To Score)")
        render_btts_analysis(df_matches, home_team, away_team)
    
    with col2:
        st.markdown("#### Draw At Least One Half")
        render_half_draw_analysis(df_matches, home_team, away_team)


def render_btts_analysis(df_matches: pd.DataFrame, home_team: str, away_team: str):
    """Render BTTS analysis."""
    
    # Get home matches for home team
    df_home = filter_matches_by_team(df_matches, home_team, venue="Home")
    # Get away matches for away team  
    df_away = filter_matches_by_team(df_matches, away_team, venue="Away")
    
    def calc_btts(df):
        if len(df) == 0:
            return 0, 0
        btts = ((df['home_score'] > 0) & (df['away_score'] > 0)).sum()
        return btts, len(df)
    
    btts_home, total_home = calc_btts(df_home)
    btts_away, total_away = calc_btts(df_away)
    
    pct_home = (btts_home / total_home * 100) if total_home > 0 else 0
    pct_away = (btts_away / total_away * 100) if total_away > 0 else 0
    
    combined = btts_home + btts_away
    combined_total = total_home + total_away
    combined_pct = (combined / combined_total * 100) if combined_total > 0 else 0
    
    st.markdown(f"""
    <div class="hitrate-card">
        <div class="hitrate-label">{home_team} (HOME)</div>
        <div class="hitrate-value">{btts_home}/{total_home}</div>
        <div class="hitrate-pct">{pct_home:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="hitrate-card">
        <div class="hitrate-label">{away_team} (AWAY)</div>
        <div class="hitrate-value">{btts_away}/{total_away}</div>
        <div class="hitrate-pct">{pct_away:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    color = COLOR_WIN if combined_pct >= 50 else COLOR_LOSE
    st.markdown(f"""
    <div class="hitrate-card">
        <div class="hitrate-label">COMBINED</div>
        <div class="hitrate-value" style="color: {color};">{combined}/{combined_total}</div>
        <div class="hitrate-pct" style="color: {color};">{combined_pct:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)


def render_half_draw_analysis(df_matches: pd.DataFrame, home_team: str, away_team: str):
    """Render Draw At Least One Half analysis."""
    
    df_home = filter_matches_by_team(df_matches, home_team, venue="Home")
    df_away = filter_matches_by_team(df_matches, away_team, venue="Away")
    
    def calc_half_draw(df):
        if len(df) == 0:
            return 0, 0
        
        count = 0
        for _, row in df.iterrows():
            # HT draw
            ht_draw = row['home_score_ht'] == row['away_score_ht']
            # 2H draw: 2H home goals == 2H away goals
            home_2h = row['home_score'] - row['home_score_ht']
            away_2h = row['away_score'] - row['away_score_ht']
            h2_draw = home_2h == away_2h
            
            if ht_draw or h2_draw:
                count += 1
        
        return count, len(df)
    
    draws_home, total_home = calc_half_draw(df_home)
    draws_away, total_away = calc_half_draw(df_away)
    
    pct_home = (draws_home / total_home * 100) if total_home > 0 else 0
    pct_away = (draws_away / total_away * 100) if total_away > 0 else 0
    
    combined = draws_home + draws_away
    combined_total = total_home + total_away
    combined_pct = (combined / combined_total * 100) if combined_total > 0 else 0
    
    st.markdown(f"""
    <div class="hitrate-card">
        <div class="hitrate-label">{home_team} (HOME)</div>
        <div class="hitrate-value">{draws_home}/{total_home}</div>
        <div class="hitrate-pct">{pct_home:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="hitrate-card">
        <div class="hitrate-label">{away_team} (AWAY)</div>
        <div class="hitrate-value">{draws_away}/{total_away}</div>
        <div class="hitrate-pct">{pct_away:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
    
    color = COLOR_WIN if combined_pct >= 50 else COLOR_LOSE
    st.markdown(f"""
    <div class="hitrate-card">
        <div class="hitrate-label">COMBINED</div>
        <div class="hitrate-value" style="color: {color};">{combined}/{combined_total}</div>
        <div class="hitrate-pct" style="color: {color};">{combined_pct:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)
