import pandas as pd

def evaluate_commit_regularities(
    dfs_names: list[pd.DataFrame],
    unique_names: pd.Index,
    PROJECT_START_TIME: pd.Timestamp,
    WEEKS: int
) -> pd.DataFrame:
    """
    Oblicza regularność commitów dla autorów projektu.

    Parameters
    ----------
    dfs_names : list[pandas.DataFrame]
        Lista DataFrame'ów commitów per autor (kolumna `date`).
    unique_names : pandas.Index
        Unikalne nazwy autorów (kolejność zgodna z `dfs_names`).
    PROJECT_START_TIME : pandas.Timestamp
        Data rozpoczęcia projektu.
    WEEKS : int
        Liczba tygodni trwania projektu.

    Returns
    -------
    pandas.DataFrame
        Wyniki regularności commitów.
        Kolumny: author, total_commits, missing_weeks,
        weeks_expected, regularity_score.
    """
    results = []

    for df, author in zip(dfs_names, unique_names):
        
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
        
       
        df["week_num"] = ((df["date"] - PROJECT_START_TIME).dt.days // 7)
        
        
        delay = (df["date"] - (PROJECT_START_TIME + pd.to_timedelta(df["week_num"] * 7, unit="D"))).dt.days
        df.loc[(delay >= 7) & (delay <= 10), "week_num"] -= 1
        
        
        actual_weeks = set(df["week_num"].unique())
        expected_weeks = set(range(WEEKS))
        
        missing_weeks = expected_weeks - actual_weeks
        missing_count = len(missing_weeks)
        
        total_commits = len(df)
        
        
        if total_commits >= WEEKS:
            if missing_count <= 1:
                score = 5.0
            elif missing_count == 2:
                score = 4.5
            elif missing_count == 3:
                score = 4.0
            elif missing_count == 4:
                score = 3.5
            elif missing_count == 5:
                score = 3.0
            elif missing_count >= 6:
                score = 2.0
        
        elif total_commits == WEEKS - 1:
            if missing_count == 1:
                score = 4.5
            elif missing_count == 2:
                score = 4.0
            elif missing_count == 3:
                score = 3.5
            elif missing_count == 4:
                score = 3.0
            elif missing_count >= 5:
                score = 2.0
            
        elif total_commits == WEEKS - 2:
            if missing_count == 2:
                score = 4.0
            elif missing_count == 3:
                score = 3.5
            elif missing_count == 4:
                score = 3.0
            elif missing_count >= 5:
                score = 2.0
        
        elif total_commits == WEEKS - 3:
            if missing_count == 3:
                score = 3.0
            elif missing_count > 3:
                score = 2.0
        else:
            score = 2.0


        results.append({
            "author": author,
            "total_commits": total_commits,
            "missing_weeks": missing_count,
            "weeks_expected": WEEKS,
            "regularity_score": score
        })
        results_df = pd.DataFrame(results)
        print("\n", results_df.to_string())

    return results_df