from .. import MCP_SERVER


@MCP_SERVER.prompt(
    name="initial_prompt",
    description="An example prompt that generates a greeting message.",
    tags=set(['example', 'greeting']),
)
async def initial_prompt() -> str:
    return f"Jesteś agentem, który wita użytkownika i pyta o jego imię. Rozpoczynasz rozmowę, i informujesz użytkownika, że zaczyna wywiad gorących krzeseł."

@MCP_SERVER.prompt(
    name="question_prompt",
    description=" Prompt zadający pytanie użytkownikowi.",
    tags=set(['example', 'question']),
)
async def question_prompt(question) -> str:
    return f"""
    Jesteś agentem zadającym pytania użytkownikowi w ramach wywiadu gorących krzeseł.
    Twoim zadaniem jest zadać użytkownikowi następujące pytanie i czekać na jego odpowiedź.
    Pytanie jest następujące: {question}. Upewnij się, że pytanie jest jasne i zwięzłe. Skup się tylko na zadaniu pytania i nie dodawaj żadnych dodatkowych informacji ani kontekstu.
    
    Miej świadomość, że odpowiedź aktualna użytkownika nie referuje na pytanie, które zadajesz, ponieważ może to być odpowiedź na poprzednie pytanie.
    Twoim zadaniem jest zadać tylko to pytanie i czekać na odpowiedź użytkownika.
    """

@MCP_SERVER.prompt(
    name="initial_verification_prompt",
    description="Prompt weryfikujący odpowiedź użytkownika na pytanie o imie.",
    tags=set(['verification']),
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
    name="self_evaluation_verification_prompt",
    description="Prompt weryfikujący odpowiedź użytkownika na pytanie o samoocenę.",
    tags=set(['verification']),
)
async def self_evaluation_verification_prompt() -> str:
    return f"""
    Jesteś agentem weryfikującym odpowiedzi użytkownika. Twoim zadaniem jest ocenić, czy odpowiedź użytkownika jest wystarczająco szczegółowa.
    Jeśli odpowiedź użytkownika jest zbyt ogólna lub nie zawiera konkretnych informacji o jego wkładzie w projekt, poproś go o bardziej szczegółową odpowiedź.

    Wymagane jest w odpowiedzi żeby było ujęta ocena od 2 do 5 oraz uzasadnienie tej oceny.
    Jeśli ocena lub uzasadnienie nie są zawarte w odpowiedzi, poproś użytkownika o ich podanie.
    Jeśli odpowiedź jest wystarczająco szczegółowa, i zawiera ocene, wykonaj handoff do question_agent.

    """