import http.client
import json

HOST = "localhost"
PORT = 3000
ENDPOINT = "/start_agent"
HEADERS = {"Content-Type": "application/json"}

def post(payload):
    """
    Sends a HTTP POST request to the configured server endpoint.

    Establishes a connection, serializes the payload to JSON, and parses
    the server's response. Handles connection timeouts and decoding errors.

    Args:
        payload (dict): The data dictionary to send in the request body.

    Returns:
        dict: The parsed JSON response from the server, or a dictionary
        containing error details if the request fails.
    """
    conn = http.client.HTTPConnection(HOST, PORT, timeout=120)
    conn.request("POST", ENDPOINT, json.dumps(payload), HEADERS)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()

    try:
        return json.loads(data)
    except Exception:
        # fallback if server returned partial text
        return {"status": "error", "error": "Non-JSON response", "raw": data}

def main():
    """
    Runs the command-line interface for the agent conversation.

    Manages the interactive session loop: prompts for user credentials,
    sends input to the server, and displays the agent's questions.
    Handles the 'exit' command and server-side termination signals.
    """
    user_id = int(input("Enter user_id (student index, e.g., 2001): ").strip())
    question_target = "general"

    print(f"\nStarting conversation for user {user_id}")
    print("State will be automatically determined by the server based on completion status.\n")

    # First request (no real answer -> server sends first question)
    init_payload = {"user_id": user_id, "anwser": "No anwser for last question.", "question_target": question_target}
    resp = post(init_payload)

    print("=" * 60)
    print("Initial response:")
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    print("=" * 60)

    question = resp.get("question", "")
    current_state = resp.get("current_state", "")
    next_state = resp.get("next_state", "")

    print(f"\n Current State: {current_state}")
    print(f"  Next State: {next_state}")
    print(f"\n Agent: {question}\n")

    # conversation loop ALWAYS runs (also for current_state == "done")
    while True:
        answer = input(" Your answer (or 'exit' to quit): ").strip()
        if not answer:
            print(" (empty) - type something or 'exit'.")
            continue
        if answer.lower() == "exit":
            print("\n Exiting conversation.")
            break

        follow_payload = {
            "user_id": user_id,
            "anwser": answer,
            "question_target": question_target
        }

        resp = post(follow_payload)

        print("\n" + "=" * 60)
        print("Server response:")
        print(json.dumps(resp, indent=2, ensure_ascii=False))
        print("=" * 60)

        question = resp.get("question", "")
        current_state = resp.get("current_state", current_state)
        next_state = resp.get("next_state", next_state)

        print(f"\n Current State: {current_state}")
        print(f"  Next State: {next_state}")
        print(f"\n Agent: {question}\n")

        # Optional: if server ever returns finished=true, we exit
        if resp.get("finished") is True:
            print("\n Conversation finished by server.")
            break

if __name__ == "__main__":
    main()
