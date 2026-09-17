import config
from llm_service import SYSTEM_PROMPT, LLMService, build_context
from memory_extraction_service import MemoryExtractionService, parse_memory_json


def generate(service, text, **overrides):
    args = dict(
        text=text, emotion="happy", energy=50, friendliness=50, curiosity=50,
        hunger=10, sleepiness=10, social_need=50, likes=["chess"], dislikes=[],
        facts=[], trust=50, friendship=50, attachment=50,
        relationship_context="You trust Hari.\nYou are friends.",
        retrieved_memories=["Plays chess"], internal_thoughts=["I'm hungry."],
        objects=["cup"], personality=None,
    )
    args.update(overrides)
    return service.generate(**args)


def test_system_prompt_is_identical_every_turn(fake_llm, user):
    service = LLMService(user)
    generate(service, "hi", energy=10)
    generate(service, "hello again", energy=90, likes=["tea"], objects=[])
    first, second = (call["messages"][0] for call in fake_llm.calls)
    assert first == second == {"role": "system", "content": SYSTEM_PROMPT}


def test_context_goes_in_last_message_and_history_stays_raw(fake_llm, user):
    fake_llm.replies = ["Meow! Chess again?"]
    service = LLMService(user)
    reply = generate(service, "want to play?")
    last = fake_llm.calls[0]["messages"][-1]
    assert last["role"] == "user"
    assert "[Context]" in last["content"] and last["content"].endswith("[User says]\nwant to play?")
    assert "User likes: chess" in last["content"]
    assert reply == "Meow! Chess again?"
    assert service.history == [{"role": "user", "content": "want to play?"},
                               {"role": "assistant", "content": "Meow! Chess again?"}]


def test_history_persists_per_user(fake_llm, user):
    service = LLMService(user)
    generate(service, "remember me")
    reloaded = LLMService(user)
    assert reloaded.history[0]["content"] == "remember me"
    reloaded.switch_user("bob")
    assert reloaded.history == []


def test_history_trimmed_in_steps(fake_llm, user):
    service = LLMService(user)
    turns = config.LLM_HISTORY_MAX // 2 + 1
    for i in range(turns):
        generate(service, f"message {i}")
    assert len(service.history) == config.LLM_HISTORY_KEEP
    assert service.history[-2]["content"] == f"message {turns - 1}"


def test_reply_cleaned(fake_llm, user):
    fake_llm.replies = ['  "Purr… how’s it going 😺"  ', ""]
    service = LLMService(user)
    assert generate(service, "hi") == "Purr... how's it going"
    assert generate(service, "hi") == "Meow!"


def test_build_context_formats_relationship_on_one_line():
    ctx = build_context("sad", 1, 2, 3, 4, 5, 6, [], [], "a\nb", [], "", [], {"laziness": 90})
    assert "Relationship: a b\n" in ctx
    assert "laziness 90" in ctx
    assert "User likes: none" in ctx


def test_long_lists_are_capped():
    ctx = build_context("sad", 1, 2, 3, 4, 5, 6, [f"x{i}" for i in range(50)], [], "", [], "", [], None)
    assert "x49" in ctx and "x39" not in ctx


def test_extraction_uses_shared_model(fake_llm):
    fake_llm.replies = ['Sure: {"likes": ["jazz"], "dislikes": [], "facts": "Lives in Kochi"}']
    assert MemoryExtractionService().extract("I love jazz and live in Kochi") == {
        "likes": ["jazz"], "dislikes": [], "facts": ["Lives in Kochi"]}


def test_parse_memory_json_handles_bad_output():
    empty = {"likes": [], "dislikes": [], "facts": []}
    assert parse_memory_json("no json here") == empty
    assert parse_memory_json("{not json}") == empty
    assert parse_memory_json('["a"]') == empty
    assert parse_memory_json('{"likes": ["tea", "  ", null]}') == {
        "likes": ["tea"], "dislikes": [], "facts": []}
