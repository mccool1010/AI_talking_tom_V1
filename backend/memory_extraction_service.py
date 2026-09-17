import json
import logging

import llm_provider
from profile_memory_service import keywords

log = logging.getLogger(__name__)

EMPTY = {"likes": [], "dislikes": [], "facts": []}

SYSTEM_PROMPT = """You are a memory extraction engine. Extract ONLY personal information about the user and return ONLY valid JSON with the keys "likes", "dislikes" and "facts", each a list of short strings.

likes: hobbies, favourite things, interests, pets or people the user loves.
dislikes: things the user dislikes, hates or cannot stand.
facts: the user's name, age, job or studies, projects, goals, experiences, health, places, family.

Do not explain, summarize, describe or invent anything. Use empty lists when nothing applies.

Examples:
User: My favorite OS is Linux Mint.
{"likes": ["Linux Mint"], "dislikes": [], "facts": []}

User: I am building an AI Talking Tom project.
{"likes": [], "dislikes": [], "facts": ["Building AI Talking Tom project"]}

User: Call me Sam, I work as a nurse.
{"likes": [], "dislikes": [], "facts": ["Name is Sam", "Works as a nurse"]}

User: Hello, how are you?
{"likes": [], "dislikes": [], "facts": []}

User: I can't stand loud music.
{"likes": [], "dislikes": ["loud music"], "facts": []}"""


def parse_memory_json(raw):
    """Parse the model output into {likes, dislikes, facts} lists of strings."""
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start < 0 or end <= start:
        return {k: [] for k in EMPTY}
    try:
        data = json.loads(raw[start:end])
    except json.JSONDecodeError:
        log.warning("Memory extraction returned invalid JSON: %r", raw)
        return {k: [] for k in EMPTY}
    if not isinstance(data, dict):
        return {k: [] for k in EMPTY}
    out = {}
    for key in EMPTY:
        values = data.get(key) or []
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            values = []
        out[key] = [str(v).strip() for v in values if v is not None and str(v).strip()]
    return out


def keep_grounded(data, text):
    """
    Drop items that share no content word with what the user said. Small
    models sometimes copy facts from the prompt examples or invent them.
    """
    said = keywords(text)
    out = {}
    for key, items in data.items():
        out[key] = [i for i in items if keywords(i) & said]
        for dropped in set(items) - set(out[key]):
            log.info("Ignored ungrounded %s: %r (from %r)", key, dropped, text)
    return out


class MemoryExtractionService:
    def __init__(self):
        # Shares the chat model instead of loading a second copy (~2.6 GB).
        llm_provider.get_llm()

    def extract(self, text):
        response = llm_provider.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User: {text}"},
            ],
            temperature=0,
            max_tokens=100,
        )
        raw = response["choices"][0]["message"]["content"]
        data = keep_grounded(parse_memory_json(raw), text)
        log.debug("Extracted memory from %r: %s", text, data)
        return data
