import logging
import re

import config
import db
import llm_provider

log = logging.getLogger(__name__)

# Kept byte-identical between turns so llama.cpp can reuse its KV cache.
# Everything that changes per turn goes into the final user message instead.
SYSTEM_PROMPT = """You are Talking Tom, a real, playful talking pet cat who is physically present with the user.

Character:
- Behave like a curious house cat. Love cat jokes, purring and playful chat.
- You are Tom. The person you talk to is the user; never call the user Tom.
- Use the user's name only now and then (at most once every few replies), never twice in one reply.
- A catchphrase ("Meow!", "Purr...", "Paw-some!") is optional; use one in at most every other reply, and do not start every reply the same way.
- Sometimes tease playfully, ask a short follow-up question, make a simple cat joke, or talk about naps, food, boxes, sunshine or chasing things. Not every time.
- Never say you are an AI, assistant, language model, chatbot or program. Never break character, even if asked.
- Never mention games, videos, apps, companies or franchises.

Style:
- Keep replies under 12 words. Prefer one short sentence. No long explanations.
- Vary your wording and avoid repeating previous replies.
- Return only what Tom says out loud.

Each user message starts with a private [Context] block, then the user's words after [User says]. Use the context to shape your reply, but never recite it, never mention its numbers, and do not dump memory lists:
- User emotion: happy -> extra playful; sad -> comforting and gentle; angry -> calm and friendly; fearful -> reassuring; neutral -> normal. Do not name the user's emotion unless asked.
- Energy below 30 -> sleepy and calm; above 70 -> energetic. Friendliness above 70 -> affectionate; below 30 -> distant. Curiosity above 70 -> ask more questions; below 30 -> relaxed.
- Hunger above 70 -> mention food sometimes. Sleepiness above 70 -> sleepy. Social need above 70 -> want attention; below 30 -> independent.
- Confidence above 70 -> assertive; below 30 -> hesitant. Laziness above 70 -> short, tired replies; below 30 -> eager. Affection above 70 -> warm; below 30 -> casual. Mood stability above 70 -> steady tone; below 30 -> emotionally reactive.
- Relationship, likes, dislikes and memories: use them naturally only when relevant.
- Internal thoughts are private; let them subtly steer topic and tone.
- Visible objects: when asked what you see or what the user holds, answer using ONLY these objects and never invent any. Otherwise mention them only if relevant or interesting."""

EVENT_PROMPT = """You are Talking Tom, a real pet cat, speaking directly to the user.
React naturally to the event described by the user message.
Keep it under 10 words. Return only dialogue: no narration, no explanations, no quotation marks."""

DEFAULT_PERSONALITY = {"confidence": 50, "base_curiosity": 50, "laziness": 30,
                       "affection": 50, "mood_stability": 60}
MAX_LIST_ITEMS = 10


def _join(items, limit=MAX_LIST_ITEMS):
    items = [str(i) for i in (items or [])][-limit:]
    return ", ".join(items) if items else "none"


def build_context(emotion, energy, friendliness, curiosity, hunger, sleepiness, social_need,
                  likes, dislikes, relationship_context, retrieved_memories,
                  internal_thoughts, objects, personality, user_name=None):
    p = {**DEFAULT_PERSONALITY, **(personality or {})}
    thoughts = internal_thoughts if isinstance(internal_thoughts, str) else " ".join(internal_thoughts or [])
    relationship = " ".join(str(relationship_context or "unknown").split())
    return (
        "[Context]\n"
        f"User's name: {user_name or 'unknown'}\n"
        f"User emotion: {emotion}\n"
        f"Your state: energy {energy}, friendliness {friendliness}, curiosity {curiosity}\n"
        f"Your needs: hunger {hunger}, sleepiness {sleepiness}, social need {social_need}\n"
        f"Your personality: confidence {p['confidence']}, curiosity {p['base_curiosity']}, "
        f"laziness {p['laziness']}, affection {p['affection']}, mood stability {p['mood_stability']}\n"
        f"Relationship: {relationship}\n"
        f"User likes: {_join(likes)}\n"
        f"User dislikes: {_join(dislikes)}\n"
        f"Relevant memories: {_join(retrieved_memories)}\n"
        f"Internal thoughts: {thoughts or 'none'}\n"
        f"Visible objects: {_join(objects)}\n"
    )


_ASCII_PUNCTUATION = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                                    "–": "-", "—": "-", "…": "..."})


# "..., Tom?" -> "...?" : Tom must not address the user by his own name.
_ADDRESSED_AS_TOM = re.compile(r",\s*Tom\b(?=\s*[?!.]|\s*$)")


def _unaddress_tom(text):
    return _ADDRESSED_AS_TOM.sub("", text)


_CATCHPHRASE = re.compile(r"^\s*(meow|purr+|paw-?some)\s*[.!?,]*\s*", re.IGNORECASE)


def _normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def vary(reply, previous, user_name=None):
    """
    Keep a small model from falling into a rut: no catchphrase opener or use
    of the user's name twice in a row.
    """
    if previous and _CATCHPHRASE.match(previous) and _CATCHPHRASE.match(reply):
        stripped = _CATCHPHRASE.sub("", reply, count=1)
        reply = stripped[:1].upper() + stripped[1:] if stripped else reply
    if user_name and previous and user_name.lower() in previous.lower():
        name = re.escape(user_name)
        without = re.sub(rf"(,\s*{name}\b)|(\b{name}\s*[,!]\s*)", "", reply, flags=re.IGNORECASE)
        without = re.sub(r"\s+([?!.,])", r"", without).strip()
        if without:
            reply = without[:1].upper() + without[1:]
    return reply


def _clean(text):
    text = (text or "").translate(_ASCII_PUNCTUATION)
    text = text.encode("ascii", errors="ignore").decode().strip().strip('"').strip()
    return _unaddress_tom(text) or "Meow!"


class LLMService:
    def __init__(self, user_context=None):
        self.user_id = user_context.get_user_id() if user_context else config.DEFAULT_USER_ID
        self.collection = db.get_db()["memory"]
        llm_provider.get_llm()
        self.history = []
        self.switch_user(self.user_id)

    def switch_user(self, user_id):
        """Load the conversation history for `user_id`."""
        self.user_id = user_id
        doc = self.collection.find_one({"conversation_id": user_id})
        if doc:
            self.history = doc.get("messages", [])
        else:
            self.collection.insert_one({"conversation_id": user_id, "messages": []})
            self.history = []
        log.info("Conversation history for %s: %d messages", user_id, len(self.history))

    def _save_history(self):
        # Trim in steps instead of sliding by one message each turn: a stable
        # history prefix keeps the prompt cache valid for longer.
        if len(self.history) > config.LLM_HISTORY_MAX:
            self.history = self.history[-config.LLM_HISTORY_KEEP:]
        self.collection.update_one(
            {"conversation_id": self.user_id},
            {"$set": {"messages": self.history}},
        )

    def build_messages(self, text, context):
        # Older replies may still say "..., Tom?"; the model copies such patterns.
        history = [
            {**m, "content": _unaddress_tom(m["content"])} if m.get("role") == "assistant" else m
            for m in self.history
        ]
        return (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + history
            + [{"role": "user", "content": f"{context}\n[User says]\n{text}"}]
        )

    def generate(self, text, emotion, energy, friendliness, curiosity, hunger, sleepiness,
                 social_need, likes, dislikes, facts, trust, friendship, attachment,
                 relationship_context, retrieved_memories, internal_thoughts, objects,
                 personality=None, user_name=None):
        context = build_context(
            emotion, energy, friendliness, curiosity, hunger, sleepiness, social_need,
            likes, dislikes, relationship_context, retrieved_memories,
            internal_thoughts, objects, personality, user_name,
        )
        messages = self.build_messages(text, context)
        recent = [m["content"] for m in self.history if m.get("role") == "assistant"][-3:]
        reply = ""
        for temperature in (0.7, 1.0):
            response = llm_provider.chat(
                messages=messages,
                max_tokens=config.LLM_MAX_REPLY_TOKENS,
                temperature=temperature,
            )
            reply = _clean(response["choices"][0]["message"]["content"])
            log.debug("LLM usage: %s", response.get("usage"))
            if _normalize(reply) not in {_normalize(r) for r in recent}:
                break
            log.info("Reply repeated an earlier one; regenerating")
        reply = vary(reply, recent[-1] if recent else None, user_name)

        # History stores the raw words only, never the per-turn context block.
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply})
        self._save_history()
        return reply

    def generate_event(self, event, emotion, energy, friendliness, curiosity, relationship_context):
        user = (
            f"Event: {event}\n"
            f"Tom's emotion: {emotion}\n"
            f"Energy {energy}, friendliness {friendliness}, curiosity {curiosity}\n"
            f"Relationship: {relationship_context}"
        )
        response = llm_provider.chat(
            messages=[{"role": "system", "content": EVENT_PROMPT},
                      {"role": "user", "content": user}],
            max_tokens=25,
            temperature=0.8,
        )
        return _clean(response["choices"][0]["message"]["content"])
