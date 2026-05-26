"""
Stat Engine for MetaRen Analytics
Handles stat computation per match including perspective switching.

Note: stats_team table only has period = "Full" and "1st Half".
2nd Half stats must be derived: 2H = Full - 1st Half
"""

import pandas as pd
from typing import Optional
from data_access import filter_matches_by_team, get_team_stat_for_match


def compute_stat_per_match(
    df_matches: pd.DataFrame, 
    df_team_stats: pd.DataFrame,
    team_name: str, 
    market: str, 
    period: str,
    venue: str = "All",
    perspective: str = "Total Match"
) -> pd.DataFrame:
    """
    Compute the relevant stat per match for a team.
    
    Args:
        df_matches: All matches dataframe
        df_team_stats: Team stats dataframe
        team_name: Team to analyze
        market: "Goals", "Corners", or "Cards"
        period: "Full", "1st Half", or "2nd Half"
        venue: "All", "Home", or "Away"
        perspective: "Total Match" (home+away totals) or "Team Only" (selected team's own stat)
    
    Returns:
        DataFrame with columns: game_id, date, stat_value, opponent
    """
    # Filter matches by venue
    df = filter_matches_by_team(df_matches, team_name, venue)
    
    if len(df) == 0:
        return pd.DataFrame(columns=['game_id', 'date', 'stat_value', 'opponent'])
    
    results = []
    
    for _, match in df.iterrows():
        game_id = match['game_id']
        stat_value = None
        
        if market == "Goals":
            if perspective == "Team Only":
                # Only the selected team's goals
                if period == "Full":
                    stat_value = match['team_score']
                elif period == "1st Half":
                    stat_value = match['team_score_ht']
                elif period == "2nd Half":
                    # Derive: Full - 1st Half
                    stat_value = match['team_score'] - match['team_score_ht']
            else:
                # Total Match: both teams' goals combined
                if period == "Full":
                    stat_value = match['total_goals']
                elif period == "1st Half":
                    stat_value = match['total_goals_ht']
                elif period == "2nd Half":
                    # Derive: Full - 1st Half
                    stat_value = match['total_goals'] - match['total_goals_ht']
        
        elif market == "Corners":
            stat_type = "Corner Kicks"
            stat_value = _compute_team_stat(
                df_team_stats, game_id, match, team_name, 
                stat_type, period, perspective
            )
        
        elif market == "Cards":
            stat_type = "Yellow Cards"
            stat_value = _compute_team_stat(
                df_team_stats, game_id, match, team_name, 
                stat_type, period, perspective
            )
        
        if stat_value is not None:
            results.append({
                'game_id': game_id,
                'date': match['date'],
                'stat_value': stat_value,
                'opponent': match['opponent']
            })
    
    return pd.DataFrame(results)


def _compute_team_stat(
    df_team_stats: pd.DataFrame,
    game_id: int,
    match: pd.Series,
    team_name: str,
    stat_type: str,
    period: str,
    perspective: str
) -> Optional[float]:
    """
    Compute a team stat (corners, cards) for a given period and perspective.
    
    Database only has "Full" and "1st Half" periods.
    2nd Half is derived: 2H = Full - 1st Half
    """
    
    if perspective == "Team Only":
        # Only the selected team's stat
        if period == "Full":
            return get_team_stat_for_match(df_team_stats, game_id, team_name, stat_type, "Full")
        
        elif period == "1st Half":
            return get_team_stat_for_match(df_team_stats, game_id, team_name, stat_type, "1st Half")
        
        elif period == "2nd Half":
            # Derive: Full - 1st Half
            team_full = get_team_stat_for_match(df_team_stats, game_id, team_name, stat_type, "Full")
            team_1h = get_team_stat_for_match(df_team_stats, game_id, team_name, stat_type, "1st Half")
            
            if team_full is not None and team_1h is not None:
                return team_full - team_1h
            return None
    
    else:
        # Total Match: both teams' stats combined
        home_team = match['home_team']
        away_team = match['away_team']
        
        if period == "Full":
            home_val = get_team_stat_for_match(df_team_stats, game_id, home_team, stat_type, "Full")
            away_val = get_team_stat_for_match(df_team_stats, game_id, away_team, stat_type, "Full")
            
            if home_val is not None and away_val is not None:
                return home_val + away_val
            return None
        
        elif period == "1st Half":
            home_val = get_team_stat_for_match(df_team_stats, game_id, home_team, stat_type, "1st Half")
            away_val = get_team_stat_for_match(df_team_stats, game_id, away_team, stat_type, "1st Half")
            
            if home_val is not None and away_val is not None:
                return home_val + away_val
            return None
        
        elif period == "2nd Half":
            # Derive: (home_full + away_full) - (home_1h + away_1h)
            home_full = get_team_stat_for_match(df_team_stats, game_id, home_team, stat_type, "Full")
            away_full = get_team_stat_for_match(df_team_stats, game_id, away_team, stat_type, "Full")
            home_1h = get_team_stat_for_match(df_team_stats, game_id, home_team, stat_type, "1st Half")
            away_1h = get_team_stat_for_match(df_team_stats, game_id, away_team, stat_type, "1st Half")
            
            if all(v is not None for v in [home_full, away_full, home_1h, away_1h]):
                return (home_full + away_full) - (home_1h + away_1h)
            return None
    
    return None


def generate_chart_key(mode: str, period: str, market: str, direction: str, 
                       line: float, team: str, perspective: str = "Total Match") -> str:
    """
    Generate a deterministic unique key for Streamlit charts.
    This prevents StreamlitDuplicateElementId errors.
    """
    # Sanitize team name for key
    team_key = team.replace(" ", "_").replace(".", "").lower()[:20]
    perspective_key = "total" if perspective == "Total Match" else "team"
    return f"chart_{mode}_{period}_{market}_{direction}_{line}_{team_key}_{perspective_key}"
