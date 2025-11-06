# server_mcp.py
from fastmcp import FastMCP
import random
import json

mcp = FastMCP("Hot Seat Game Server")

#Baza pytań
questions_db = [
    "Jakie jest twoje ulubione danie?",
    "Gdzie chciałbyś pojechać na wakacje?",
    "Jaki jest twój ulubiony film?",
    "Co lubisz robić w wolnym czasie?",
    "Jaką supermoc chciałbyś mieć?",
    "Jaki jest twój ulubiony kolor?",
    "Jakiego zwierzaka chciałbyś mieć?",
    "Jakie jest twoje hobby?",
]


game_state = {
    "current_question": None,
    "players": [],
    "scores": {},
}

@mcp.tool()
def get_random_question() -> str:
    """Losuje nowe pytanie."""
    q = random.choice(questions_db)
    game_state["current_question"] = q
    return q

@mcp.tool()
def get_current_question() -> dict:
    """Zwraca aktualne pytanie."""
    return {
        "question": game_state["current_question"],
        "active": game_state["current_question"] is not None,
    }

@mcp.tool()
def add_player(player_name: str) -> dict:
    """Dodaje gracza."""
    if player_name not in game_state["players"]:
        game_state["players"].append(player_name)
        game_state["scores"][player_name] = 0
    return {
        "player": player_name,
        "added": True,
        "total_players": len(game_state["players"]),
    }

@mcp.tool()
def update_score(player_name: str, points: int) -> dict:
    """Aktualizuje wynik gracza."""
    if player_name in game_state["scores"]:
        game_state["scores"][player_name] += points
    else:
        game_state["scores"][player_name] = points
        if player_name not in game_state["players"]:
            game_state["players"].append(player_name)
    return {
        "player": player_name,
        "new_score": game_state["scores"][player_name],
        "updated": True,
    }

@mcp.tool()
def get_leaderboard() -> dict:
    """Zwraca ranking."""
    sorted_scores = sorted(game_state["scores"].items(), key=lambda x: x[1], reverse=True)
    return {
        "leaderboard": [{"player": n, "score": s} for n, s in sorted_scores],
        "total_players": len(sorted_scores),
    }

@mcp.resource("resource://game-state")
def get_game_state() -> str:
    """Pełny stan gry w JSON."""
    return json.dumps(game_state, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run()
