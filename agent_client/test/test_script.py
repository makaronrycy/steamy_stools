import http.client
import json

HOST = "localhost"
PORT = 3000
ENDPOINT = "/start_agent"
HEADERS = {"Content-Type": "application/json"}

def post(payload):
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
    init_payload = {"session_id": "test_user_1", "answer": ""}
    resp = post(init_payload)
    print("Initial response:")
    print(resp)

    question = resp.get("question", "")
    print("\nAgent question:\n", question)

    while True:
        answer = input("\nYour answer (empty to exit): ").strip()
        if not answer:
            break
        
        follow_payload = {"session_id": "test_user_1", "answer": answer}
        resp = post(follow_payload)
        print("\nServer response:")
        print(resp)
        print("\nAgent:", resp.get("question", ""))

if __name__ == "__main__":
    main()
