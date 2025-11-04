import pandas as pd

def evaluate_commit_regularities(dfs_names, unique_names, PROJECT_START_TIME, WEEKS):
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
            if missing_weeks <= 1:
                score = 5.0
            elif missing_weeks == 2:
                score = 4.5
            elif missing_weeks == 3:
                score = 4.0
            elif missing_weeks == 4:
                score = 3.5
            elif missing_weeks == 5:
                score = 3.0
            elif missing_weeks >= 6:
                score = 2.0
        
        elif total_commits == WEEKS - 1:
            if missing_weeks == 1:
                score = 4.5
            elif missing_weeks == 2:
                score = 4.0
            elif missing_weeks == 3:
                score = 3.5
            elif missing_weeks == 4:
                score = 3.0
            elif missing_weeks >= 5:
                score = 2.0
            
        elif total_commits == WEEKS - 2:
            if missing_weeks == 2:
                score = 4.0
            elif missing_weeks == 3:
                score = 3.5
            elif missing_weeks == 4:
                score = 3.0
            elif missing_weeks >= 5:
                score = 2.0
        
        elif total_commits == WEEKS - 3:
            if missing_weeks == 3:
                score = 3.0
            elif missing_weeks > 3:
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