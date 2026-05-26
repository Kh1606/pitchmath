"""
Team Analyzer Component for MetaRen Analytics
Single team form analysis with betting lines + Team DNA.
"""

import streamlit as st
import pandas as pd
from typing import Optional

from ui_style import get_team_color, COLOR_WIN, COLOR_LOSE
from data_access import filter_matches_by_team
from logic.stat_engine import compute_stat_per_match, generate_chart_key
from components.charts import render_line_visualization, render_single_hit_rate_card
from components.team_dna import render_team_dna


def render_team_analyzer_sidebar(available_teams: list) -> dict:
    """Render Team Analyzer specific sidebar options."""
    st.sidebar.markdown("### 📊 Team Selection")
    
    if not available_teams:
        st.sidebar.warning("No teams available for selected competition.")
        return {"team": None, "venue_filter": "All"}
    
    team = st.sidebar.selectbox(
        "Select Team",
        available_teams,
        index=0,
        key="team_analyzer_team"
    )
    
    st.sidebar.markdown("#### 🏟️ Venue")
    venue_filter = st.sidebar.radio(
        "Venue Filter",
        ["All", "Home", "Away"],
        index=0,
        key="venue_filter",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    return {
        "team": team,
        "venue_filter": venue_filter,
    }


def render_team_analyzer_main(selections: dict, df_matches: pd.DataFrame, 
                               df_team_stats: pd.DataFrame, df_players: pd.DataFrame):
    """Render main Team Analyzer page."""
    
    team = selections.get("team")
    venue_filter = selections.get("venue_filter", "All")
    
    if not team:
        st.warning("Please select a team in the sidebar.")
        return
    
    # Get filtered matches (df_matches is already filtered by season+competition upstream)
    df_team = filter_matches_by_team(df_matches, team, venue_filter)
    
    if len(df_team) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No matches found for selected filters.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Render team header
    team_color = get_team_color(team)
    st.markdown(f"""
    <div class="match-header-card" style="border-left: 4px solid {team_color};">
        <div class="match-header-teams">{team}</div>
        <div class="match-header-ht">{venue_filter} Matches | {len(df_team)} Games</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Summary metrics row
    render_team_summary_metrics(df_team, df_team_stats, team)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2 = st.tabs(["📈 Betting Lines", "🧬 Team DNA"])
    
    with tab1:
        render_team_betting_lines(df_matches, df_team_stats, team, venue_filter)
    
    with tab2:
        # Use the new Team DNA with 3 tabs (Radar, Control Zones, Percentile Ranks)
        render_team_dna(df_team, df_team_stats, df_players, team)


def render_team_summary_metrics(df_team: pd.DataFrame, df_team_stats: pd.DataFrame, 
                                 team_name: str):
    """Render summary metrics row for team."""
    
    total_games = len(df_team)
    wins = len(df_team[df_team['result'] == 'Win'])
    draws = len(df_team[df_team['result'] == 'Draw'])
    losses = len(df_team[df_team['result'] == 'Loss'])
    
    avg_scored = df_team['team_score'].mean()
    avg_conceded = df_team['opponent_score'].mean()
    
    # Get corners and cards from team stats
    game_ids = df_team['game_id'].tolist()
    team_stats = df_team_stats[
        (df_team_stats['game_id'].isin(game_ids)) &
        (df_team_stats['team_name'].str.contains(team_name, case=False, na=False))
    ]
    
    corners = team_stats[
        (team_stats['stat_type'] == 'Corner Kicks') & 
        (team_stats['period'] == 'Full')
    ]['value'].mean()
    corners = corners if not pd.isna(corners) else 0
    
    yellows = team_stats[
        (team_stats['stat_type'] == 'Yellow Cards') & 
        (team_stats['period'] == 'Full')
    ]['value'].mean()
    yellows = yellows if not pd.isna(yellows) else 0
    
    team_color = get_team_color(team_name)
    
    cols = st.columns(6)
    metrics = [
        (f"{total_games}", "Games", "#FFFFFF"),
        (f"{wins}W-{draws}D-{losses}L", "Record", "#FFFFFF"),
        (f"{avg_scored:.1f}", "Avg Scored", team_color),
        (f"{avg_conceded:.1f}", "Avg Conceded", COLOR_LOSE),
        (f"{corners:.1f}", "Avg Corners", "#FFFFFF"),
        (f"{yellows:.1f}", "Avg Cards", "#FFC107")
    ]
    
    for col, (value, label, color) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {color};">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def render_team_betting_lines(df_matches: pd.DataFrame, df_team_stats: pd.DataFrame,
                               team: str, venue: str):
    """Render betting lines analysis for single team."""
    
    st.markdown("### 📈 Betting Line Analysis")
    
    # Key prefix for unique keys
    key_prefix = "team_betting"
    
    # Perspective toggle
    perspective = st.radio(
        "Perspective",
        ["Total Match", "Team Only"],
        index=0,
        horizontal=True,
        key=f"{key_prefix}_perspective",
        help="Total Match: combined stats from both teams. Team Only: selected team's own stat."
    )
    
    # Market and period selectors
    col1, col2 = st.columns(2)
    with col1:
        market = st.selectbox(
            "Select Market",
            ["Goals", "Corners", "Cards"],
            key=f"{key_prefix}_market"
        )
    with col2:
        if market == "Corners":
            # Corners only available for Full match (no reliable 1H data)
            st.selectbox(
                "Select Period",
                ["Full"],
                key=f"{key_prefix}_period_corners_locked",
                disabled=True,
                help="Corners are only available for Full match (1H corners not reliable)"
            )
            period = "Full"
        else:
            period = st.selectbox(
                "Select Period",
                ["Full", "1st Half", "2nd Half"],
                key=f"{key_prefix}_period"
            )
    
    # Line and direction
    if market == "Goals":
        lines = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
        default_line = 2.5
    elif market == "Corners":
        lines = [5.5, 6.5, 7.5, 8.5, 9.5, 10.5, 11.5]
        default_line = 9.5
    else:
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
    
    # Compute stats with perspective
    df_stats = compute_stat_per_match(
        df_matches, df_team_stats, team, 
        market, period, venue=venue, perspective=perspective
    )
    
    team_color = get_team_color(team)
    
    # Generate unique chart key
    chart_key = generate_chart_key("team", period, market, direction, line, team, perspective)
    
    perspective_label = "" if perspective == "Total Match" else " (Team Stats Only)"
    
    hits, total = render_line_visualization(
        df_stats, team, line, direction, team_color,
        f"{team} - {market} ({period}){perspective_label}",
        chart_key
    )
    
    # Hit rate display
    render_single_hit_rate_card(hits, total, direction, line)
