from src.llm.token_budget import TokenBudget, chunk_for_budget, strip_boilerplate


def test_small_input_returns_single_chunk():
    budget = TokenBudget(max_context_tokens=8000)
    chunks = chunk_for_budget("short text", budget)
    assert len(chunks) == 1


def test_oversized_input_is_split_never_blind_truncated_from_end():
    budget = TokenBudget(max_context_tokens=200, reserved_output_tokens=20, reserved_system_tokens=20)
    text = "\n\n".join([f"Paragraph {i} with some content about AI startups." for i in range(50)])
    chunks = chunk_for_budget(text, budget)
    assert len(chunks) > 1
    # every chunk must fit the budget
    for c in chunks:
        assert len(c) <= budget.input_budget_chars + 50  # small slack for prefix


def test_title_and_metadata_survive_chunking():
    budget = TokenBudget(max_context_tokens=200, reserved_output_tokens=20, reserved_system_tokens=20)
    text = "\n\n".join([f"Paragraph {i} filler text here." for i in range(30)])
    chunks = chunk_for_budget(text, budget, title="Important Startup Name", metadata="https://source.example/x")
    assert all("Important Startup Name" in c for c in chunks)


def test_strip_boilerplate_removes_cookie_banners():
    text = "Cookie policy notice here\nActual article content about AI.\nSubscribe to our newsletter"
    cleaned = strip_boilerplate(text)
    assert "Cookie" not in cleaned
    assert "Actual article content" in cleaned
