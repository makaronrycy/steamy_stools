from .. import MCP_SERVER


@MCP_SERVER.prompt(
    name="initial_prompt",
    description="An example prompt that generates a greeting message.",
    tags=set(['example', 'greeting']),
)
async def initial_prompt() -> str:
    return f"Jesteś agentem, który wita użytkownika i pyta o jego imię. Rozpoczynasz rozmowę, i powiedz że zaczynasz wywiad gorących krzeseł."

@MCP_SERVER.prompt(
    name="question_prompt",
    description=" Prompt zadający pytanie użytkownikowi.",
    tags=set(['example', 'question']),
)
async def question_prompt(question) -> str:
    return f"""Prompt z następującym pytaniem: {question}. Upewnij się, że pytanie jest jasne i zwięzłe."""

@MCP_SERVER.prompt(
    name="verification_prompt",
    description="Prompt weryfikujący odpowiedź użytkownika.",
    tags=set(['example', 'verification']),
)
async def initial_verification_prompt() -> str:
    return f"""
    Jesteś agentem weryfikującym odpowiedzi użytkownika. Twoim zadaniem jest ocenić, czy odpowiedź jest zgodna z oczekiwaniami.
    Masz dostęp do następującego narzędzia: check_name_tool, które sprawdza, czy podane imie i nazwisko jest w bazie danych.
    Wywoływanie narzędzia powinno być wykonane, jeśli odpowiedź użytkownika zawiera imię i nazwisko.
    Dane wejściowe do check_name_tool:
    {{
        "first_name": "<imię>",
        "last_name": "<nazwisko>"
    }}
    Jeśli odpowiedź użytkownika nie zawiera imienia i nazwiska, zadaj ponowne pytanie o imię i nazwisko.
    Jeśli imię i nazwisko znajdują się w bazie danych, wykonaj handoff do question_agent.
    Jeśli imię i nazwisko nie znajdują się w bazie danych, poinformuj użytkownika, że nie ma jego imienia w bazie danych i poproś o poprawne podanie imienia.
    """

@MCP_SERVER.prompt(
    name="mood_question_prompt",
    description="Zadaj jedno, zwięzłe pytanie o nastrój. Zwróć tylko treść pytania."
)
def mood_question_prompt() -> str:
    return (
        "Masz zadać jedno uprzejme pytanie o nastrój użytkownika. "
        "Tylko treść pytania, po polsku. Przykład stylu: 'Jak się dziś czujesz?'."
    )

@MCP_SERVER.prompt(
    name="mood_classify_prompt",
    description="Sklasyfikuj odpowiedź o nastrój i zwróć krótki komentarz jako JSON."
)
def mood_classify_prompt() -> str:
    return (
        "Dostaniesz w wejściu:\n"
        "Pytanie: <tekst>\n"
        "Odpowiedź użytkownika: <tekst>\n"
        "Zwróć TYLKO surowy JSON: "
        "{\"label\":\"bad|okay|good\",\"comment\":\"jedno krótkie zdanie po polsku\"}"
    )
