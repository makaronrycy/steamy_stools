from .. import MCP_SERVER


@MCP_SERVER.prompt(
    name="initial_prompt",
    description="An example prompt that generates a greeting message.",
    tags=set(['example', 'greeting']),
)
async def initial_prompt() -> str:
    return f"Your task is to greet the user warmly, and ask them for their name."

@MCP_SERVER.prompt(
    name="question_prompt",
    description=" Prompt zadający pytanie użytkownikowi.",
    tags=set(['example', 'question']),
)
async def question_prompt(question) -> str:
    return f"Prompt z następującym pytaniem: {question}. Upewnij się, że pytanie jest jasne i zwięzłe." .format(question=question),

@MCP_SERVER.prompt(
    name="verification_prompt",
    description="Prompt weryfikujący odpowiedź użytkownika.",
    tags=set(['example', 'verification']),
)
async def verification_prompt() -> str:
    return f"Twoim zadaniem jest zweryfikowanie odpowiedzi użytkownika na pytanie. Sprawdź, czy odpowiedź jest poprawna i zgodna z pytaniem."

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
