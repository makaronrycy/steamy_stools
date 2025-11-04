import http.client
import json

HOST = "localhost"
PORT = 3000
ENDPOINT = "/start_agent"
HEADERS = {"Content-Type": "application/json"}

def post(payload):
    # use plain HTTP for a non-TLS local server
    conn = http.client.HTTPConnection(HOST, PORT,timeout=120)
    conn.request("POST", ENDPOINT, json.dumps(payload), HEADERS)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    try:
        return json.loads(data)
    except Exception:
        return {"raw": data}

def main():
    """
    Simplified test script - only sends user_id and answer.
    Server determines state automatically based on completion status.
    """
    # Get user_id at the start
    user_id = input("Enter user_id (student index, e.g., 2001): ").strip()
    if not user_id:
        print("Error: user_id is required")
        return

    question_target = "general"  # Optional, defaults to "general" on server

    print(f"\nStarting conversation for user {user_id}")
    print("State will be automatically determined by the server based on completion status.\n")

    # Initial request - no answer yet
    init_payload = {
        "user_id": user_id,
        "anwser": "",  # Empty answer for initial request
        "question_target": question_target
    }

    resp = post(init_payload)
    print("=" * 60)
    print("Initial response:")
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    print("=" * 60)

    question = resp.get("question", "")
    next_state = resp.get("next_state", "")
    current_state = resp.get("current_state", "")

    print(f"\n Current State: {current_state}")
    print(f"  Next State: {next_state}")
    print(f"\n Agent: {question}\n")

    # Conversation loop
    while next_state != "done":
        answer = input(" Your answer (or 'exit' to quit): ").strip()
        if not answer or answer.lower() == 'exit':
            print("\n Exiting conversation.")
            break

        # Simplified payload - only user_id and answer required
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

        # Extract response info
        question = resp.get("question", "")
        next_state = resp.get("next_state", next_state)
        current_state = resp.get("current_state", current_state)

        print(f"\n Current State: {current_state}")
        print(f"  Next State: {next_state}")

        if next_state == "done":
            print("\n All assessments completed!")
            print(f"\n Agent: {question}\n")
            break
        else:
            print(f"\n Agent: {question}\n")

if __name__ == "__main__":
    main()
