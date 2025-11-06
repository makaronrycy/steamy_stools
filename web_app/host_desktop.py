# host_desktop_openai.py
import customtkinter as ctk
import asyncio
import websockets
import json
import threading
from openai import OpenAI
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class HotSeatGameApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gorące Krzesła - LLM (OpenAI)")
        self.geometry("900x700")

        self.websocket = None
        self.ws_url = "ws://localhost:8000/ws"

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ Brak OPENAI_API_KEY")
        self.openai_client = OpenAI(api_key=api_key)

        self.setup_ui()

    def setup_ui(self):
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkLabel(main_container, text="GORĄCE KRZESŁA", font=ctk.CTkFont(size=24, weight="bold"))
        header.pack(pady=(0, 20))

        question_frame = ctk.CTkFrame(main_container, corner_radius=10)
        question_frame.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(question_frame, text="❓ Aktualne pytanie:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.question_label = ctk.CTkLabel(question_frame, text="Kliknij 'Losuj pytanie' aby rozpocząć", font=ctk.CTkFont(size=16), wraplength=800, justify="left")
        self.question_label.pack(fill="x", padx=15, pady=(5, 15))

        chat_frame = ctk.CTkFrame(main_container, corner_radius=10)
        chat_frame.pack(fill="both", expand=True, pady=(0, 15))
        ctk.CTkLabel(chat_frame, text="💬 Czat z LLM (GPT):", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        self.chat_display = ctk.CTkTextbox(chat_frame, height=300, font=ctk.CTkFont(size=12), wrap="word")
        self.chat_display.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        input_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        input_frame.pack(fill="x", pady=(0, 15))
        self.input_field = ctk.CTkEntry(input_frame, placeholder_text="Wpisz wiadomość...", font=ctk.CTkFont(size=13), height=40)
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.input_field.bind("<Return>", lambda e: self.send_message())
        self.send_btn = ctk.CTkButton(input_frame, text="📤 Wyślij", command=self.send_message, width=100, height=40, font=ctk.CTkFont(size=13, weight="bold"))
        self.send_btn.pack(side="left")

        button_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        button_frame.pack(fill="x")
        self.question_btn = ctk.CTkButton(button_frame, text="🎲 Losuj pytanie", command=self.get_question, width=140, height=40, fg_color="#3498DB", hover_color="#2980B9")
        self.question_btn.pack(side="left", padx=(0, 10))
        self.leaderboard_btn = ctk.CTkButton(button_frame, text="🏆 Ranking", command=self.show_leaderboard, width=140, height=40, fg_color="#E74C3C", hover_color="#C0392B")
        self.leaderboard_btn.pack(side="left", padx=(0, 10))
        self.connect_btn = ctk.CTkButton(button_frame, text="🔌 Połącz WS", command=self.connect_websocket, width=140, height=40, fg_color="#9B59B6", hover_color="#8E44AD")
        self.connect_btn.pack(side="left")

        self.status_label = ctk.CTkLabel(main_container, text="⚪ Rozłączony", font=ctk.CTkFont(size=11), text_color="gray")
        self.status_label.pack(pady=(10, 0))

    def append_message(self, sender, message):
        self.chat_display.insert("end", f"{sender}: {message}\n\n")
        self.chat_display.see("end")

    def connect_websocket(self):
        self.connect_btn.configure(state="disabled", text="Łączenie...")
        threading.Thread(target=self._connect_ws_thread, daemon=True).start()

    def _connect_ws_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_connect())

    async def _ws_connect(self):
        try:
            # parametry keepalive; zmniejsz ryzyko „no close frame”
            self.websocket = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5
            )
            self.after(0, lambda: self.status_label.configure(text="🟢 Połączono WebSocket", text_color="green"))
            self.after(0, lambda: self.connect_btn.configure(state="normal", text="✅ Połączono", fg_color="#27AE60"))
            self.append_message("System", "Połączono z serwerem WebSocket")
            await self._ws_listener()
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text="🔴 Błąd połączenia", text_color="red"))
            self.after(0, lambda: self.connect_btn.configure(state="normal", text="🔌 Połącz WS"))
            self.append_message("Błąd", str(e))

    async def _ws_listener(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data.get("type") == "tool_response":
                    tool = data.get("tool")
                    payload = data.get("data", {})
                    if "error" in payload:
                        self.after(0, lambda err=payload["error"]: self.append_message("Błąd MCP", err))
                        continue
                    result = payload.get("result", None)

                    if tool == "get_random_question":
                        if isinstance(result, str):
                            self.after(0, lambda q=result: self.question_label.configure(text=q))
                            self.after(0, lambda q=result: self.append_message("System", f"Nowe pytanie: {q}"))
                        else:
                            self.after(0, lambda: self.append_message("System", "Brak pytania"))

                    elif tool == "get_leaderboard":
                        if isinstance(result, dict):
                            leaderboard = result.get("leaderboard", [])
                            text = "🏆 RANKING:\n\n"
                            for i, entry in enumerate(leaderboard, 1):
                                text += f"{i}. {entry['player']}: {entry['score']} pkt\n"
                            self.after(0, lambda t=text: self.append_message("System", t))
                        else:
                            self.after(0, lambda: self.append_message("System", "Brak rankingu"))
                elif data.get("type") == "update":
                    pass
        except websockets.exceptions.ConnectionClosed:
            self.after(0, lambda: self.append_message("System", "Połączenie WebSocket zamknięte"))
        except Exception as e:
            self.after(0, lambda err=str(e): self.append_message("Błąd WS", err))

    def get_question(self):
        if not self.websocket:
            self.append_message("Błąd", "Najpierw połącz się z WebSocket!")
            return
        self.question_btn.configure(state="disabled")
        threading.Thread(target=self._send_tool_request, args=("get_random_question", {}), daemon=True).start()
        self.after(1000, lambda: self.question_btn.configure(state="normal"))

    def show_leaderboard(self):
        if not self.websocket:
            self.append_message("Błąd", "Najpierw połącz się z WebSocket!")
            return
        self.leaderboard_btn.configure(state="disabled")
        threading.Thread(target=self._send_tool_request, args=("get_leaderboard", {}), daemon=True).start()
        self.after(1000, lambda: self.leaderboard_btn.configure(state="normal"))

    def _send_tool_request(self, tool_name, arguments):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_send(tool_name, arguments))

    async def _async_send(self, tool_name, arguments):
        try:
            await self.websocket.send(json.dumps({"tool": tool_name, "arguments": arguments}))
        except Exception as e:
            self.after(0, lambda err=str(e): self.append_message("Błąd", err))

    def send_message(self):
        msg = self.input_field.get().strip()
        if not msg:
            return
        self.input_field.delete(0, "end")
        self.append_message("Ty", msg)
        self.send_btn.configure(state="disabled")
        threading.Thread(target=self._chat_with_llm, args=(msg,), daemon=True).start()

    def _chat_with_llm(self, message):
        try:
            resp = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Jesteś pomocnym asystentem w grze 'Gorące krzesła'."},
                    {"role": "user", "content": message},
                ],
                max_tokens=512,
                temperature=0.7,
            )
            reply = resp.choices[0].message.content
            self.after(0, lambda r=reply: self.append_message("🤖 GPT", r))
        except Exception as e:
            self.after(0, lambda err=str(e): self.append_message("Błąd LLM", err))
        finally:
            self.after(0, lambda: self.send_btn.configure(state="normal"))

if __name__ == "__main__":
    app = HotSeatGameApp()
    app.mainloop()
