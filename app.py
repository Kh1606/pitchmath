#!/usr/bin/env python3
"""
MetaRen - Football Analytics & Betting App
REFACTORED: Modular architecture with isolated components.

Features:
- Match Analyzer (default): Head-to-head betting analysis with line engine
- Team Analyzer: Single team form with betting lines + Team DNA
- Player Analyzer: Player props and performance tracking
- Fixtures: Upcoming match schedule from all extracted competitions

Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Local imports
from ui_style import inject_custom_css
from data_access import (
    load_matches,
    load_team_stats,
    load_player_stats,
    load_upcoming_fixtures,
    get_available_teams,
    get_available_seasons,
    get_competitions_for_season,
    format_season_label,
)
from components.match_analyzer import render_match_analyzer_main, render_match_analyzer_sidebar
from components.team_analyzer import render_team_analyzer_main, render_team_analyzer_sidebar
from components.player_analyzer import render_player_analyzer_main, render_player_analyzer_sidebar


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="MetaRen | Football Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =============================================================================
# COUNTRY DISPLAY MAPPING
# =============================================================================

# Map DB country values to display labels with flag emojis
COUNTRY_DISPLAY = {
    "England": "🏴 England",
    "Spain": "🇪🇸 Spain",
    "Italy": "🇮🇹 Italy",
    "Germany": "🇩🇪 Germany",
    "France": "🇫🇷 France",
    "World": "🌍 Europe/UEFA",
}


# =============================================================================
# FIXTURES PAGE
# =============================================================================

def render_fixtures_page(selected_season: int, selected_competition_id: int):
    """Render the upcoming fixtures schedule page."""
    st.markdown("""
    <div class="dashboard-header">
        <h1>📅 Upcoming Fixtures</h1>
        <p>Schedule for selected competition & season</p>
    </div>
    """, unsafe_allow_html=True)

    df_upcoming = load_upcoming_fixtures(
        season=selected_season,
        competition_id=selected_competition_id
    )

    if df_upcoming is None or len(df_upcoming) == 0:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📅</div>
            <p>No upcoming fixtures found for this competition/season.</p>
            <p style="font-size: 0.9rem; color: #6B7280;">
                Try selecting a different competition or run the extractor to populate fixture data.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Round filter (if data available)
    rounds = df_upcoming["round"].dropna().unique().tolist()
    if len(rounds) > 1:
        rounds_sorted = sorted(rounds)
        selected_round = st.selectbox(
            "Filter by Round",
            ["All"] + rounds_sorted,
            key="fixtures_round_filter"
        )
        if selected_round != "All":
            df_upcoming = df_upcoming[df_upcoming["round"] == selected_round]

    if len(df_upcoming) == 0:
        st.info("No fixtures match the selected filters.")
        return

    st.markdown(f"**{len(df_upcoming)} upcoming match(es)**")

    # Group by date
    df_upcoming["date_display"] = pd.to_datetime(df_upcoming["date"]).dt.strftime("%A, %B %d, %Y")
    df_upcoming["time_display"] = pd.to_datetime(df_upcoming["date"]).dt.strftime("%H:%M")

    for date_label, group in df_upcoming.groupby("date_display", sort=False):
        st.markdown(f"#### 📆 {date_label}")

        for _, row in group.iterrows():
            league = row.get("league_name", "")
            rnd = row.get("round", "")
            venue = row.get("venue_name", "")
            time_str = row.get("time_display", "")

            meta_parts = [league]
            if rnd:
                meta_parts.append(rnd)
            if venue:
                meta_parts.append(f"🏟 {venue}")

            meta_str = " • ".join(meta_parts)

            st.markdown(f"""
            <div class="match-card">
                <div class="match-date">{time_str} — {meta_str}</div>
                <div class="match-teams">{row['home_team']}  vs  {row['away_team']}</div>
            </div>
            """, unsafe_allow_html=True)

            # Analyze button
            btn_key = f"fx_btn_{row['game_id']}"
            if st.button(f"⚽ Analyze {row['home_team']} vs {row['away_team']}", key=btn_key):
                st.session_state["nav_mode"] = "Match Analyzer"
                st.session_state["nav_season"] = int(row["season"])
                st.session_state["nav_competition_id"] = int(row["competition_id"])
                st.session_state["nav_home_team"] = row["home_team"]
                st.session_state["nav_away_team"] = row["away_team"]
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR RENDERING
# =============================================================================

def render_sidebar(df_matches_all: pd.DataFrame) -> dict:
    """Render sidebar with season, country, competition, mode selection and filters."""

    st.sidebar.caption("⚽ MetaRen Analytics")
    st.sidebar.markdown("---")

    # ------------------------------------------------------------------
    # 1) SEASON SELECTOR
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 📅 Season")
    available_seasons = get_available_seasons()
    if not available_seasons:
        st.sidebar.warning("No seasons found in database.")
        return {"mode": "Match Analyzer"}

    season_labels = [format_season_label(s) for s in available_seasons]

    # Handle navigation from fixtures
    nav_season = st.session_state.pop("nav_season", None)
    nav_comp_id = st.session_state.pop("nav_competition_id", None)
    nav_mode = st.session_state.pop("nav_mode", None)
    nav_home = st.session_state.pop("nav_home_team", None)
    nav_away = st.session_state.pop("nav_away_team", None)

    # Determine default season index
    default_season_idx = 0
    if nav_season is not None and nav_season in available_seasons:
        default_season_idx = available_seasons.index(nav_season)

    selected_season_label = st.sidebar.selectbox(
        "Select Season",
        season_labels,
        index=default_season_idx,
        key="season_select",
        label_visibility="collapsed"
    )
    selected_season = available_seasons[season_labels.index(selected_season_label)]

    st.sidebar.markdown("---")

    # ------------------------------------------------------------------
    # 2) COUNTRY → COMPETITION SELECTORS
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 🏆 Competition")

    comps_df = get_competitions_for_season(selected_season)
    if comps_df is None or len(comps_df) == 0:
        st.sidebar.warning("No competitions found for this season.")
        return {"mode": "Match Analyzer"}

    # Build country groups
    countries_in_data = comps_df["country"].unique().tolist()
    # Sort with a preferred order
    country_order = ["England", "Spain", "Italy", "Germany", "France", "World"]
    countries_sorted = [c for c in country_order if c in countries_in_data]
    # Add any others not in our preferred order
    for c in countries_in_data:
        if c not in countries_sorted:
            countries_sorted.append(c)

    country_display_options = [COUNTRY_DISPLAY.get(c, c) for c in countries_sorted]

    # Default country index (handle nav)
    default_country_idx = 0
    if nav_comp_id is not None:
        nav_row = comps_df[comps_df["competition_id"] == nav_comp_id]
        if len(nav_row) > 0:
            nav_country = nav_row.iloc[0]["country"]
            if nav_country in countries_sorted:
                default_country_idx = countries_sorted.index(nav_country)

    selected_country_display = st.sidebar.selectbox(
        "Country / Region",
        country_display_options,
        index=default_country_idx,
        key="country_select",
        label_visibility="collapsed"
    )
    selected_country = countries_sorted[country_display_options.index(selected_country_display)]

    # Filter competitions for selected country
    country_comps = comps_df[comps_df["country"] == selected_country].copy()
    comp_names = country_comps["name"].tolist()
    comp_ids = country_comps["competition_id"].tolist()

    # Default competition index (handle nav)
    default_comp_idx = 0
    if nav_comp_id is not None and nav_comp_id in comp_ids:
        default_comp_idx = comp_ids.index(nav_comp_id)

    selected_comp_name = st.sidebar.selectbox(
        "Competition",
        comp_names,
        index=default_comp_idx,
        key="competition_select",
        label_visibility="collapsed"
    )
    selected_competition_id = comp_ids[comp_names.index(selected_comp_name)]

    st.sidebar.markdown("---")

    # ------------------------------------------------------------------
    # 3) MODE SELECTOR
    # ------------------------------------------------------------------
    st.sidebar.markdown("### 🎯 Analysis Mode")

    mode_options = ["Match Analyzer", "Team Analyzer", "Player Analyzer", "📅 Fixtures"]
    default_mode_idx = 0
    if nav_mode and nav_mode in mode_options:
        default_mode_idx = mode_options.index(nav_mode)

    mode = st.sidebar.radio(
        "Select Mode",
        mode_options,
        index=default_mode_idx,
        key="mode_selector",
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    # ------------------------------------------------------------------
    # 4) FILTER DATAFRAMES
    # ------------------------------------------------------------------
    # Filter matches to selected season + competition
    df_filtered = df_matches_all[
        (df_matches_all["season"] == selected_season) &
        (df_matches_all["competition_id"] == selected_competition_id)
    ].copy()

    # For fixtures mode, skip team selectors
    if mode == "📅 Fixtures":
        return {
            "mode": mode,
            "selected_season": selected_season,
            "selected_competition_id": selected_competition_id,
            "df_matches": df_filtered,
        }

    # Get available teams from filtered matches
    available_teams = get_available_teams(df_filtered)

    selections = {
        "mode": mode,
        "selected_season": selected_season,
        "selected_competition_id": selected_competition_id,
        "available_teams": available_teams,
        "df_matches": df_filtered,
        "nav_home_team": nav_home,
        "nav_away_team": nav_away,
    }

    # Mode-specific selectors
    if mode == "Match Analyzer":
        selections.update(
            render_match_analyzer_sidebar(df_filtered, available_teams, nav_home, nav_away)
        )
    elif mode == "Team Analyzer":
        selections.update(render_team_analyzer_sidebar(available_teams))
    elif mode == "Player Analyzer":
        selections.update(render_player_analyzer_sidebar(df_filtered, available_teams))

    return selections


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""

    # Inject custom CSS
    inject_custom_css()

    # Load data
    try:
        df_matches_all = load_matches()
        df_team_stats = load_team_stats()
        df_players_all = load_player_stats()
    except Exception as e:
        st.error(f"""
        **Database Error:** Could not load data.

        Please ensure you have run the extractor first to populate the database.

        ```bash
        python -m extractors.run --config configs/country/england/epl.yml
        ```

        Error: {str(e)}
        """)
        return

    # Render sidebar and get selections
    selections = render_sidebar(df_matches_all)

    mode = selections.get("mode", "Match Analyzer")
    selected_season = selections.get("selected_season")
    selected_competition_id = selections.get("selected_competition_id")

    # --- Fixtures page (standalone) ---
    if mode == "📅 Fixtures":
        render_fixtures_page(selected_season, selected_competition_id)
        return

    # --- Analytics pages ---
    # Use filtered matches from sidebar
    df_matches = selections.get("df_matches", pd.DataFrame())

    # Filter players by game_ids in the filtered matches
    if len(df_matches) > 0:
        filtered_game_ids = set(df_matches["game_id"].tolist())
        df_players = df_players_all[df_players_all["game_id"].isin(filtered_game_ids)].copy()
    else:
        df_players = pd.DataFrame()

    if len(df_matches) == 0:
        st.markdown(f"""
        <div class="dashboard-header">
            <h1>⚽ MetaRen Analytics</h1>
            <p>{mode} | Football Betting Intelligence</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="empty-state">
            <div class="empty-state-icon">📭</div>
            <p>No played matches found for the selected season & competition.</p>
            <p style="font-size: 0.9rem; color: #6B7280;">
                Try a different season or competition, or run the extractor.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Render header based on mode
    st.markdown(f"""
    <div class="dashboard-header">
        <h1>⚽ MetaRen Analytics</h1>
        <p>{mode} | Football Betting Intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    # Route to appropriate page
    if mode == "Match Analyzer":
        render_match_analyzer_main(selections, df_matches, df_team_stats)
    elif mode == "Team Analyzer":
        render_team_analyzer_main(selections, df_matches, df_team_stats, df_players)
    elif mode == "Player Analyzer":
        render_player_analyzer_main(selections, df_matches, df_players)

    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #4B5563; font-size: 0.8rem; padding: 1rem;">
        MetaRen Analytics | Match-Centric Betting Analyzer
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
