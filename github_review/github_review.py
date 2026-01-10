from fastapi import FastAPI
from code_metrics import full_github_review

app = FastAPI(title="GitHub Review API", version="1.0")

@app.post("/analyze")
def analyze_repo():

    full_github_review()

    return {"message": "Analiza została wykonana"}
