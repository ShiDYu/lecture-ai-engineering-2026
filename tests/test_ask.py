from types import SimpleNamespace

from app import ask as ask_module


def test_main_keeps_chat_history_for_follow_up_questions(monkeypatch, capsys):
    sent_messages = []

    class FakeChat:
        def send_message(self, question):
            sent_messages.append(question)
            return SimpleNamespace(
                text=f"answer to {question}",
                usage_metadata=SimpleNamespace(
                    prompt_token_count=10,
                    candidates_token_count=5,
                ),
            )

    chat = FakeChat()
    created_chats = []

    def create_chat(model):
        created_chats.append(model)
        return chat

    monkeypatch.setattr(
        ask_module.genai,
        "Client",
        lambda **kwargs: SimpleNamespace(
            chats=SimpleNamespace(create=create_chat)
        ),
    )
    monkeypatch.setattr(ask_module, "get_api_key", lambda: "test-key")
    monkeypatch.setattr("sys.argv", ["app.ask", "first question"])
    questions = iter(["follow-up question", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(questions))

    ask_module.main()

    output = capsys.readouterr().out
    assert sent_messages == ["first question", "follow-up question"]
    assert created_chats == [ask_module.MODEL]
    assert output.count("[usage] input=10, output=5") == 2
    assert "answer to follow-up question" in output