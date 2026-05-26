"""
Team DNA Component for MetaRen Analytics
Uses EXACT code provided by user with 3 tabs: Radar, Control Zones, Percentile Ranks.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui_style import get_team_color, COLOR_WIN, COLOR_LOSE


def render_team_dna(df_team: pd.DataFrame, df_stats: pd.DataFrame, 
                   df_players: pd.DataFrame, team_name: str):
    """Render Team DNA widget with Radar, Zones, and Ranks."""
    
    st.markdown('<div class="widget-title">🧬 Team DNA</div>', unsafe_allow_html=True)
    
    tab_radar, tab_zones, tab_ranks = st.tabs(["📊 Radar", "🎯 Control Zones", "📈 Percentile Ranks"])
    
    with tab_radar:
        render_dna_radar(df_team, df_stats, df_players, team_name)
    
    with tab_zones:
        render_control_zones(df_players, team_name)
    
    with tab_ranks:
        render_percentile_ranks(df_team, df_stats, df_players, team_name)


def render_dna_radar(df_team: pd.DataFrame, df_stats: pd.DataFrame, 
                    df_players: pd.DataFrame, team_name: str):
    """Render polar/radar chart comparing offensive vs defensive metrics."""
    
    game_ids = df_team['game_id'].tolist()
    team_players = df_players[
        (df_players['game_id'].isin(game_ids)) &
        (df_players['team_name'].str.contains(team_name, case=False, na=False))
    ]
    
    if len(team_players) == 0:
        st.info("No player data available for radar chart.")
        return
    
    # Aggregate stats per game then average
    agg_stats = team_players.groupby('game_id').agg({
        'shots_total': 'sum',
        'shots_on': 'sum',
        'passes_total': 'sum',
        'key_passes': 'sum',
        'tackles': 'sum',
        'interceptions': 'sum',
        'duels_won': 'sum',
        'dribbles_success': 'sum'
    }).mean()
    
    # Normalize to 0-100 scale for radar
    max_vals = {
        'shots_total': 20,
        'shots_on': 10,
        'passes_total': 600,
        'key_passes': 15,
        'tackles': 25,
        'interceptions': 15,
        'duels_won': 60,
        'dribbles_success': 15
    }
    
    categories = ['Shots', 'Shots on Target', 'Passing Volume', 'Key Passes',
                  'Tackles', 'Interceptions', 'Duels Won', 'Dribbles']
    
    values = [
        min(agg_stats['shots_total'] / max_vals['shots_total'] * 100, 100),
        min(agg_stats['shots_on'] / max_vals['shots_on'] * 100, 100),
        min(agg_stats['passes_total'] / max_vals['passes_total'] * 100, 100),
        min(agg_stats['key_passes'] / max_vals['key_passes'] * 100, 100),
        min(agg_stats['tackles'] / max_vals['tackles'] * 100, 100),
        min(agg_stats['interceptions'] / max_vals['interceptions'] * 100, 100),
        min(agg_stats['duels_won'] / max_vals['duels_won'] * 100, 100),
        min(agg_stats['dribbles_success'] / max_vals['dribbles_success'] * 100, 100)
    ]
    
    team_color = get_team_color(team_name)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],  # Close the shape
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor=f'rgba({int(team_color[1:3], 16)}, {int(team_color[3:5], 16)}, {int(team_color[5:7], 16)}, 0.3)',
        line=dict(color=team_color, width=2),
        name=team_name
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                showticklabels=False,
                gridcolor='#333333'
            ),
            angularaxis=dict(
                gridcolor='#333333',
                linecolor='#333333'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888888', size=10),
        showlegend=False,
        height=350,
        margin=dict(l=60, r=60, t=30, b=30)
    )
    
    # Unique key for radar chart
    team_key = team_name.replace(" ", "_").lower()[:20]
    st.plotly_chart(fig, use_container_width=True, key=f"dna_radar_{team_key}")


def render_control_zones(df_players: pd.DataFrame, team_name: str):
    """Render midfield control metrics."""
    
    team_players = df_players[
        df_players['team_name'].str.contains(team_name, case=False, na=False)
    ]
    
    if len(team_players) == 0:
        st.info("No player data available.")
        return
    
    # Calculate control metrics
    total_duels = team_players['duels_total'].sum()
    duels_won = team_players['duels_won'].sum()
    duels_pct = (duels_won / total_duels * 100) if total_duels > 0 else 0
    
    avg_interceptions = team_players.groupby('game_id')['interceptions'].sum().mean()
    avg_tackles = team_players.groupby('game_id')['tackles'].sum().mean()
    avg_blocks = team_players.groupby('game_id')['blocks'].sum().mean()
    
    # Display metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {COLOR_WIN if duels_pct >= 50 else COLOR_LOSE};">
                {duels_pct:.1f}%
            </div>
            <div class="metric-label">Duels Won Rate</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_interceptions:.1f}</div>
            <div class="metric-label">Avg Interceptions</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_tackles:.1f}</div>
            <div class="metric-label">Avg Tackles</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_blocks:.1f}</div>
            <div class="metric-label">Avg Blocks</div>
        </div>
        """, unsafe_allow_html=True)


def render_percentile_ranks(df_team: pd.DataFrame, df_stats: pd.DataFrame,
                           df_players: pd.DataFrame, team_name: str):
    """Render text-based percentile list."""
    
    # For demo purposes, calculate some percentiles based on available data
    # In production, you'd compare against league averages
    
    game_ids = df_team['game_id'].tolist()
    team_players = df_players[
        (df_players['game_id'].isin(game_ids)) &
        (df_players['team_name'].str.contains(team_name, case=False, na=False))
    ]
    
    if len(team_players) == 0:
        st.info("No data available for percentile calculation.")
        return
    
    # Calculate per-game averages
    per_game = team_players.groupby('game_id').agg({
        'shots_total': 'sum',
        'tackles': 'sum',
        'interceptions': 'sum',
        'duels_won': 'sum',
        'key_passes': 'sum'
    }).mean()
    
    # Mock percentile ranks (in production, compare to league)
    metrics = [
        ("Shot Volume", min(per_game['shots_total'] / 15 * 100, 99), COLOR_WIN),
        ("High Pressing", min(per_game['tackles'] / 20 * 100, 99), COLOR_WIN),
        ("Ball Recovery", min(per_game['interceptions'] / 12 * 100, 99), "#6366F1"),
        ("Duel Dominance", min(per_game['duels_won'] / 50 * 100, 99), "#6366F1"),
        ("Chance Creation", min(per_game['key_passes'] / 12 * 100, 99), COLOR_WIN)
    ]
    
    for label, pct, color in metrics:
        tier = "Elite" if pct >= 90 else "Top 25%" if pct >= 75 else "Above Avg" if pct >= 50 else "Below Avg"
        st.markdown(f"""
        <div class="percentile-row">
            <span class="percentile-label">{label}</span>
            <div class="percentile-bar-bg">
                <div class="percentile-bar-fill" style="width: {pct}%; background: {color};"></div>
            </div>
            <span class="percentile-value">{pct:.0f}%</span>
        </div>
        """, unsafe_allow_html=True)
        
        if pct >= 75:
            st.caption(f"  ↳ {tier}")
