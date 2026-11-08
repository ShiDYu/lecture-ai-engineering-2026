"""学習記録は利用者が承認したときだけ保存する（API呼び出しなし）。"""

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel

from app import agent as agent_module
from app import tools


@pytest.mark.parametrize("answer", ["y", "n", "", EOFError, KeyboardInterrupt])
def test_save_requires_user_approval(tmp_path, monkeypatch, capsys, answer):
    log_dir = tmp_path / "learning_log"
    monkeypatch.setattr(tools, "LEARNING_LOG_DIR", log_dir)

    def respond(messages, info):
        if any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            return ModelResponse(parts=[TextPart("完了")])
        return ModelResponse(parts=[ToolCallPart(
            "save_learning_log", {"lecture": 2, "content": "PEFTを学んだ。"},
            tool_call_id="save-1",
        )])

    def confirm(prompt):
        assert not log_dir.exists()
        preview = capsys.readouterr().out
        assert "learning_log/" in preview
        assert '"lecture": 2' in preview
        assert "PEFTを学んだ。" in preview
        if isinstance(answer, type):
            raise answer()
        return answer

    monkeypatch.setattr(agent_module, "build_model", lambda: FunctionModel(respond))
    monkeypatch.setattr("builtins.input", confirm)
    monkeypatch.setattr("sys.argv", ["app.agent", "第2回の学習記録を保存して"])
    agent_module.main()

    if answer == "y":
        records = list(log_dir.glob("*.md"))
        assert len(records) == 1
        assert records[0].read_text(encoding="utf-8") == "# 第2回の学習記録\n\nPEFTを学んだ。\n"
        tools.save_learning_log(2, "別の記録")
        assert len(list(log_dir.glob("*.md"))) == 2
        assert "PEFTを学んだ。" in records[0].read_text(encoding="utf-8")
    else:
        assert not log_dir.exists()
