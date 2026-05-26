"""
Player Analyzer Component for MetaRen Analytics
Player props and performance tracking.

Selection UI lives in the main content area (not sidebar).
"""

import streamlit as st
import pandas as pd

from ui_style import get_team_color, COLOR_WIN, COLOR_LOSE
from components.charts import render_player_bar_chart, render_player_props_chart, render_single_hit_rate_card


def render_player_analyzer_sidebar(df_matches: pd.DataFrame, available_teams: list) -> dict:
    """
    Sidebar for Player Analyzer mode.
    Team / position / player selection has been moved to the main area,
    so this just returns the available_teams for the main function to use.
    """
    return {"available_teams_for_players": available_teams}


def render_player_analyzer_main(selections: dict, df_matches: pd.DataFrame, 
                                 df_players: pd.DataFrame):
    """Render main Player Analyzer page."""
    
    available_teams = selections.get("available_teams_for_players",
                                     selections.get("available_teams", []))
    
    if not available_teams:
        st.warning("No teams available for selected competition.")
        return
    
    # -----------------------------------------------------------------
    # Player Selection — in main content area
    # -----------------------------------------------------------------
    st.markdown("### 👤 Player Selection")
    
    sel_col1, sel_col2, sel_col3 = st.columns(3)
    
    with sel_col1:
        team = st.selectbox(
            "Select Team",
            available_teams,
            index=0,
            key="player_analyzer_team"
        )
    
    with sel_col2:
        position_tab = st.radio(
            "Position",
            ["FW", "MF", "DF", "GK"],
            index=0,
            key="position_tab",
            horizontal=True
        )
    
    # Filter players for team
    team_players = df_players[df_players['team_name'].str.contains(team, case=False, na=False)]
    
    if len(team_players) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No player data available for this team.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Filter by position
    position_map = {
        "FW": ["F", "FW", "CF", "ST", "LW", "RW"],
        "MF": ["M", "MF", "CM", "CAM", "CDM", "LM", "RM", "AM"],
        "DF": ["D", "DF", "CB", "LB", "RB", "LWB", "RWB"],
        "GK": ["G", "GK"]
    }
    
    position_keywords = position_map.get(position_tab, [position_tab])
    
    if 'position' in team_players.columns:
        pos_mask = team_players['position'].fillna('').str.upper().apply(
            lambda x: any(pk in x for pk in position_keywords)
        )
        filtered_players = team_players[pos_mask]
        
        if len(filtered_players) == 0:
            filtered_players = team_players
            st.info(f"No {position_tab} players found. Showing all positions.")
    else:
        filtered_players = team_players
    
    # Get unique players sorted by goals desc, then minutes desc
    player_agg = filtered_players.groupby('player_name').agg({
        'goals': 'sum',
        'minutes': 'sum',
        'game_id': 'count'
    }).reset_index()
    player_agg = player_agg.sort_values(['goals', 'minutes'], ascending=[False, False])
    player_names = player_agg['player_name'].tolist()
    
    if not player_names:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No players found for selected position.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    with sel_col3:
        selected_player = st.selectbox(
            "Select Player",
            player_names,
            key="player_selector"
        )
    
    st.markdown("---")
    
    # -----------------------------------------------------------------
    # Player data
    # -----------------------------------------------------------------
    player_stats = filtered_players[filtered_players['player_name'] == selected_player].copy()
    player_stats = player_stats.sort_values('date')
    
    # Player summary
    render_player_summary(player_stats, selected_player, team)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2 = st.tabs(["📊 Metrics", "🎯 Prop Lines"])
    
    with tab1:
        render_player_metrics(player_stats, selected_player)
    
    with tab2:
        render_player_props(player_stats, selected_player)


def render_player_summary(player_stats: pd.DataFrame, player_name: str, team_name: str):
    """Render player summary metrics."""
    
    games = len(player_stats)
    total_minutes = player_stats['minutes'].sum()
    total_goals = player_stats['goals'].sum() if 'goals' in player_stats.columns else 0
    total_assists = player_stats['assists'].sum() if 'assists' in player_stats.columns else 0
    
    avg_shots = player_stats['shots_total'].mean() if 'shots_total' in player_stats.columns else 0
    avg_sot = player_stats['shots_on'].mean() if 'shots_on' in player_stats.columns else 0
    
    team_color = get_team_color(team_name)
    
    st.markdown(f"""
    <div class="match-header-card" style="border-left: 4px solid {team_color};">
        <div class="match-header-teams">{player_name}</div>
        <div class="match-header-ht">{team_name}</div>
    </div>
    """, unsafe_allow_html=True)
    
    cols = st.columns(6)
    metrics = [
        (f"{games}", "Games", "#FFFFFF"),
        (f"{total_minutes}", "Minutes", "#FFFFFF"),
        (f"{total_goals}", "Goals", team_color),
        (f"{total_assists}", "Assists", "#6366F1"),
        (f"{avg_shots:.1f}", "Avg Shots", "#FFFFFF"),
        (f"{avg_sot:.1f}", "Avg SoT", COLOR_WIN)
    ]
    
    for col, (value, label, color) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {color};">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def render_player_metrics(player_stats: pd.DataFrame, player_name: str):
    """Render player per-match metrics visualization."""
    
    st.markdown("### 📊 Per-Match Performance")
    
    # Metric selector
    available_metrics = []
    metric_labels = {
        'shots_total': 'Total Shots',
        'shots_on': 'Shots on Target',
        'goals': 'Goals',
        'assists': 'Assists',
        'key_passes': 'Key Passes',
        'dribbles_success': 'Successful Dribbles',
        'duels_won': 'Duels Won',
        'tackles': 'Tackles',
        'interceptions': 'Interceptions',
        'blocks': 'Blocks',
        'yellow_cards': 'Yellow Cards',
        'minutes': 'Minutes Played'
    }
    
    for col, label in metric_labels.items():
        if col in player_stats.columns and player_stats[col].sum() > 0:
            available_metrics.append((col, label))
    
    if not available_metrics:
        st.info("No metric data available for this player.")
        return
    
    selected_metric = st.selectbox(
        "Select Metric",
        [m[0] for m in available_metrics],
        format_func=lambda x: dict(available_metrics)[x],
        key="player_metric"
    )
    
    df = player_stats.copy()
    
    # Generate unique chart key
    player_key = player_name.replace(" ", "_").lower()[:20]
    chart_key = f"player_metrics_{player_key}_{selected_metric}"
    
    render_player_bar_chart(
        df, selected_metric, player_name, 
        dict(available_metrics)[selected_metric],
        chart_key
    )
    
    # Detailed table with Team Against column
    st.markdown("#### 📋 Match Details")
    
    display_cols = ['date']
    # Build Team Against from home_team / away_team columns
    has_opponent_info = ('home_team' in player_stats.columns and 
                         'away_team' in player_stats.columns and
                         'team_name' in player_stats.columns)
    
    if has_opponent_info:
        display_cols.append('team_against')
    
    display_cols.append('minutes')
    for col in ['shots_total', 'shots_on', 'goals', 'assists', 'key_passes', 
                 'dribbles_success', 'duels_won', 'tackles']:
        if col in player_stats.columns:
            display_cols.append(col)
    
    display_df = player_stats.copy()
    display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
    
    if has_opponent_info:
        display_df['team_against'] = display_df.apply(
            lambda row: row['away_team'] if str(row['team_name']).lower() == str(row['home_team']).lower()
                        else row['home_team'],
            axis=1
        )
    
    # Filter to only columns that exist
    display_cols = [c for c in display_cols if c in display_df.columns]
    
    # Rename for display
    rename_map = {
        'date': 'Date',
        'team_against': 'Team Against',
        'minutes': 'Min',
        'shots_total': 'Shots',
        'shots_on': 'SoT',
        'goals': 'G',
        'assists': 'A',
        'key_passes': 'KP',
        'dribbles_success': 'Drib',
        'duels_won': 'Duels',
        'tackles': 'Tkl',
    }
    
    st.dataframe(
        display_df[display_cols].rename(columns=rename_map),
        use_container_width=True,
        hide_index=True
    )


def render_player_props(player_stats: pd.DataFrame, player_name: str):
    """Render player prop lines analysis."""
    
    st.markdown("### 🎯 Prop Lines Analysis")
    
    # Metric selector
    prop_metrics = {
        'shots_total': 'Total Shots',
        'shots_on': 'Shots on Target',
        'goals': 'Goals',
        'assists': 'Assists',
        'key_passes': 'Key Passes + Assists',
        'tackles': 'Tackles'
    }
    
    available_props = [(k, v) for k, v in prop_metrics.items() 
                       if k in player_stats.columns and player_stats[k].sum() > 0]
    
    if not available_props:
        st.info("No prop data available for this player.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_prop = st.selectbox(
            "Select Prop",
            [m[0] for m in available_props],
            format_func=lambda x: dict(available_props)[x],
            key="player_prop"
        )
    
    with col2:
        lines = [0.5, 1.5, 2.5, 3.5, 4.5]
        line = st.select_slider(
            "Select Line",
            options=lines,
            value=0.5,
            key="player_prop_line"
        )
    
    direction = st.radio(
        "Direction",
        ["Over", "Under"],
        index=0,
        horizontal=True,
        key="player_prop_direction"
    )
    
    st.markdown("---")
    
    df = player_stats.copy()
    
    # Generate unique chart key
    player_key = player_name.replace(" ", "_").lower()[:20]
    chart_key = f"player_props_{player_key}_{selected_prop}_{line}_{direction}"
    
    hits, total = render_player_props_chart(
        df, selected_prop, line, direction,
        player_name, dict(available_props)[selected_prop],
        chart_key
    )
    
    # Hit rate display
    render_single_hit_rate_card(hits, total, direction, line)
