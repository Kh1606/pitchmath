"""
Plotly Charts for MetaRen Analytics
All chart rendering functions with deterministic unique keys.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Tuple

from ui_style import get_team_color, COLOR_WIN, COLOR_LOSE


def render_line_visualization(
    df_stats: pd.DataFrame, 
    team_name: str, 
    line: float, 
    direction: str, 
    team_color: str,
    title: str,
    chart_key: str
) -> Tuple[int, int]:
    """
    Render stacked bar visualization for a single team's stat values.
    Returns (hits, total) tuple.
    """
    
    if len(df_stats) == 0:
        st.markdown(f"""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No data available for {team_name}</p>
        </div>
        """, unsafe_allow_html=True)
        return 0, 0
    
    df = df_stats.copy().sort_values('date')
    
    # Calculate hit/miss based on direction
    if direction == "Over":
        df['hit'] = df['stat_value'] > line
    else:
        df['hit'] = df['stat_value'] < line
    
    hits = df['hit'].sum()
    total = len(df)
    
    # Create bar colors
    colors = [COLOR_WIN if hit else COLOR_LOSE for hit in df['hit']]
    
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=list(range(len(df))),
        y=df['stat_value'],
        marker_color=colors,
        text=df['stat_value'].astype(int),
        textposition='inside',
        textfont=dict(color='white', size=12),
        hovertemplate='vs %{customdata}<br>Value: %{y}<extra></extra>',
        customdata=df['opponent']
    ))
    
    # Add reference line
    fig.add_hline(y=line, line_dash="dash", line_color="#FFFFFF", 
                  annotation_text=f"Line: {line}", annotation_position="right")
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color='#E5E7EB')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#8B9DC3'),
        xaxis=dict(
            showticklabels=False,
            showgrid=False
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#2D3548',
            dtick=1
        ),
        height=250,
        margin=dict(l=40, r=40, t=50, b=20),
        showlegend=False
    )
    
    # Use the provided unique key
    st.plotly_chart(fig, use_container_width=True, key=chart_key)
    
    return hits, total


def render_hit_rate_cards(hits_a: int, total_a: int, hits_b: int, total_b: int,
                          team_a: str, team_b: str, direction: str, line: float):
    """Render hit rate summary cards for Match Analyzer."""
    
    pct_a = (hits_a / total_a * 100) if total_a > 0 else 0
    pct_b = (hits_b / total_b * 100) if total_b > 0 else 0
    
    combined_hits = hits_a + hits_b
    combined_total = total_a + total_b
    combined_pct = (combined_hits / combined_total * 100) if combined_total > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        color = COLOR_WIN if pct_a >= 50 else COLOR_LOSE
        st.markdown(f"""
        <div class="hitrate-card">
            <div class="hitrate-label">{team_a} (HOME)</div>
            <div class="hitrate-value" style="color: {color};">{hits_a}/{total_a}</div>
            <div class="hitrate-pct" style="color: {color};">{pct_a:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        color = COLOR_WIN if pct_b >= 50 else COLOR_LOSE
        st.markdown(f"""
        <div class="hitrate-card">
            <div class="hitrate-label">{team_b} (AWAY)</div>
            <div class="hitrate-value" style="color: {color};">{hits_b}/{total_b}</div>
            <div class="hitrate-pct" style="color: {color};">{pct_b:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        color = COLOR_WIN if combined_pct >= 50 else COLOR_LOSE
        st.markdown(f"""
        <div class="hitrate-card">
            <div class="hitrate-label">COMBINED</div>
            <div class="hitrate-value" style="color: {color};">{combined_hits}/{combined_total}</div>
            <div class="hitrate-pct" style="color: {color};">{combined_pct:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)


def render_single_hit_rate_card(hits: int, total: int, direction: str, line: float):
    """Render single hit rate card for Team Analyzer."""
    pct = (hits / total * 100) if total > 0 else 0
    color = COLOR_WIN if pct >= 50 else COLOR_LOSE
    
    st.markdown(f"""
    <div class="hitrate-card" style="max-width: 300px; margin: 1rem auto;">
        <div class="hitrate-label">{direction} {line} Hit Rate</div>
        <div class="hitrate-value" style="color: {color};">{hits}/{total}</div>
        <div class="hitrate-pct" style="color: {color};">{pct:.0f}%</div>
    </div>
    """, unsafe_allow_html=True)


def render_player_bar_chart(
    df: pd.DataFrame, 
    metric_col: str, 
    player_name: str, 
    metric_label: str,
    chart_key: str
):
    """Render player per-match bar chart."""
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=list(range(len(df))),
        y=df[metric_col],
        marker_color='#6366F1',
        text=df[metric_col].astype(int),
        textposition='inside',
        textfont=dict(color='white'),
        hovertemplate='Match %{x+1}<br>Value: %{y}<extra></extra>'
    ))
    
    # Add average line
    avg_val = df[metric_col].mean()
    fig.add_hline(y=avg_val, line_dash="dash", line_color=COLOR_WIN,
                  annotation_text=f"Avg: {avg_val:.1f}", annotation_position="right")
    
    fig.update_layout(
        title=f"{player_name} - {metric_label} per Match",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E5E7EB'),
        xaxis=dict(
            title="Match",
            showgrid=False,
            tickmode='linear'
        ),
        yaxis=dict(
            title=metric_label,
            showgrid=True,
            gridcolor='#2D3548'
        ),
        height=350,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True, key=chart_key)


def render_player_props_chart(
    df: pd.DataFrame, 
    selected_prop: str, 
    line: float, 
    direction: str,
    player_name: str, 
    prop_label: str,
    chart_key: str
) -> Tuple[int, int]:
    """Render player props bar chart with hit/miss coloring. Returns (hits, total)."""
    
    # Calculate hit/miss
    if direction == "Over":
        df = df.copy()
        df['hit'] = df[selected_prop] > line
    else:
        df = df.copy()
        df['hit'] = df[selected_prop] < line
    
    hits = df['hit'].sum()
    total = len(df)
    
    # Create visualization
    colors = [COLOR_WIN if hit else COLOR_LOSE for hit in df['hit']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=list(range(len(df))),
        y=df[selected_prop],
        marker_color=colors,
        text=df[selected_prop].astype(int),
        textposition='inside',
        textfont=dict(color='white')
    ))
    
    fig.add_hline(y=line, line_dash="dash", line_color="#FFFFFF",
                  annotation_text=f"Line: {line}", annotation_position="right")
    
    fig.update_layout(
        title=f"{player_name} - {prop_label}",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E5E7EB'),
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2D3548'),
        height=300,
        margin=dict(l=50, r=50, t=50, b=30)
    )
    
    st.plotly_chart(fig, use_container_width=True, key=chart_key)
    
    return hits, total
