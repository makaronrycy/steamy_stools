import http.client
import json

HOST = "localhost"
PORT = 3000
ENDPOINT = "/start_agent"
HEADERS = {"Content-Type": "application/json"}

def post(payload):
    # use plain HTTP for a non-TLS local server
    conn = http.client.HTTPConnection(HOST, PORT)
    conn.request("POST", ENDPOINT, json.dumps(payload), HEADERS)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    conn.close()
    try:
        return json.loads(data)
    except Exception:
        return {"raw": data}

def main():
    init_payload = {"state": "initial", "last_state": "", "anwser": ""}
    resp = post(init_payload)
    print("Initial response:")
    print(resp)

    question = resp.get("question", "")
    next_state = resp.get("next_state", "mood")
    current_state = resp.get("current_state", "initial")
    print("\nAgent question:\n", question)
    print("Next state:", next_state, "Current state:", current_state)

    while True:
        answer = input("\nYour answer (empty to exit): ").strip()
        if not answer:
            break
        follow_payload = {"state": next_state, "last_state": current_state, "anwser": answer}
        resp = post(follow_payload)
        print("\nServer response:")
        print(resp)
        # update for next turn
        next_state = resp.get("next_state", next_state)
        current_state = resp.get("current_state", current_state)

if __name__ == "__main__":
    main()
