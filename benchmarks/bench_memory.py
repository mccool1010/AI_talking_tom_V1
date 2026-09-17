"""
Memory system: extraction, retention, retrieval and forgetting.

30 labelled statements go through the real extraction model and
ProfileMemoryService (scratch database). Then:
- retained: is the statement's keyword stored in the profile?
- retrieval: for a follow-up question per statement, is the right memory in
  the top 3 of ProfileMemoryService.retrieve() (what main.py uses)?
- noise: do 10 unrelated questions retrieve anything?
- forgetting: how many daily decay runs until an unused memory is removed.

Usage: python benchmarks/bench_memory.py
"""
import json
import sys
import re
import time
from datetime import datetime, timedelta

from common import RESULTS_DIR, drop_bench_db, progress

# (statement, category, keyword that must be stored, follow-up question)
CASES = [
    ("I love playing football on weekends.", "likes", "football", "Do you remember which sport I enjoy playing?"),
    ("My favourite food is biryani.", "likes", "biryani", "What should I cook for dinner, maybe biryani?"),
    ("I really enjoy listening to jazz music.", "likes", "jazz", "Can you play some jazz for me?"),
    ("I like reading science fiction novels.", "likes", "science fiction", "Any science fiction book suggestions?"),
    ("Chess is my favourite board game.", "likes", "chess", "Want to play chess with me?"),
    ("I love going hiking in the mountains.", "likes", "hiking", "Should I go hiking this weekend?"),
    ("I adore my dog Bruno.", "likes", "bruno", "Guess what Bruno did today?"),
    ("I enjoy painting with watercolors.", "likes", "watercolor", "I bought new watercolor paper."),
    ("I hate waking up early.", "dislikes", "waking up early", "I have to wake up early tomorrow."),
    ("I can't stand spicy food.", "dislikes", "spicy", "The restaurant only has spicy dishes."),
    ("I dislike rainy weather.", "dislikes", "rain", "It looks like rain today."),
    ("I really hate traffic jams.", "dislikes", "traffic", "I was stuck in traffic again."),
    ("I don't like horror movies.", "dislikes", "horror", "My friends want to watch a horror film."),
    ("Mathematics homework is something I hate.", "dislikes", "math", "I have math homework tonight."),
    ("My name is Hari.", "facts", "hari", "Do you know my name, is it Hari?"),
    ("I am a computer science student.", "facts", "computer science", "My computer science exam is next week."),
    ("I am building a robot for my college project.", "facts", "robot", "The robot finally moved today!"),
    ("My sister lives in Bangalore.", "facts", "bangalore", "I'm flying to Bangalore tomorrow."),
    ("I work part time at a coffee shop.", "facts", "coffee shop", "Busy day at the coffee shop."),
    ("I was born in Kerala.", "facts", "kerala", "I miss Kerala so much."),
    ("I am learning to play the guitar.", "facts", "guitar", "My guitar teacher was impressed."),
    ("My goal is to become a game developer.", "facts", "game developer", "How do I become a game developer?"),
    ("I have a cat named Luna.", "facts", "luna", "Luna scratched the sofa."),
    ("I am 21 years old.", "facts", "21", "Is 21 too young to start a company?"),
    ("I am allergic to peanuts.", "facts", "peanut", "Is there peanut in this cookie?"),
    ("I play the piano every evening.", "likes", "piano", "I practiced piano for two hours."),
    ("I moved to Chennai last year.", "facts", "chennai", "Chennai is so hot today."),
    ("I drive a red Honda.", "facts", "honda", "My Honda broke down."),
    ("I'm training for a marathon.", "facts", "marathon", "The marathon is in two weeks."),
    ("I hate doing laundry.", "dislikes", "laundry", "Ugh, laundry day again."),
]

UNRELATED = ["What time is it?", "Tell me a joke.", "How is the weather?", "I am tired.",
             "Can you sing a song?", "What is your name?", "I went to the shop.", "Is it a good day?",
             "Let me think about it.", "Where are you?"]


def mentions(values, keyword):
    """Whole-word(-prefix) match, so 'rain' does not match 'training'."""
    pattern = re.compile(r"\b" + re.escape(keyword), re.IGNORECASE)
    return any(pattern.search(v) for v in values)


def days_until_forgotten(importance):
    import memory_decay_service
    from memory_decay_service import MemoryDecayService

    decay = MemoryDecayService()
    learned = datetime.now()
    profile = {"likes": [], "dislikes": [], "facts": [{
        "value": "x", "importance": importance,
        "learned_at": learned.isoformat(), "last_accessed": learned.isoformat()}]}
    real_datetime = memory_decay_service.datetime
    try:
        for day in range(1, 400):
            class FrozenDay(real_datetime):
                @classmethod
                def now(cls, tz=None, _day=day):
                    return learned + timedelta(days=_day)
            memory_decay_service.datetime = FrozenDay
            decay.decay(profile)
            decay.remove_forgotten_memories(profile)
            if not profile["facts"]:
                return day
    finally:
        memory_decay_service.datetime = real_datetime
    return None


def main():
    from memory_extraction_service import MemoryExtractionService
    from profile_memory_service import ProfileMemoryService

    drop_bench_db()
    extractor = MemoryExtractionService()
    profile = ProfileMemoryService()

    rows = []
    for k, (statement, category, keyword, _) in enumerate(CASES, 1):
        progress("extracting", k, len(CASES))
        start = time.perf_counter()
        data = extractor.extract(statement)
        seconds = time.perf_counter() - start
        for item in data["likes"]:
            profile.add_like(item)
        for item in data["dislikes"]:
            profile.add_dislike(item)
        for item in data["facts"]:
            profile.add_fact(item)
        rows.append({"statement": statement, "category": category, "keyword": keyword,
                     "extracted": data, "seconds": seconds,
                     "right_category": mentions(data[category], keyword),
                     "any_category": mentions(sum(data.values(), []), keyword)})

    stored = {c: [m["value"] for m in profile.get_profile()[c]] for c in ("likes", "dislikes", "facts")}
    everything = sum(stored.values(), [])
    for r in rows:
        r["retained"] = mentions(everything, r["keyword"])

    hits, precision, latency = 0, [], []
    for (_, _, keyword, question), r in zip(CASES, rows):
        start = time.perf_counter()
        found = [m["value"] for m in profile.retrieve(question, limit=3)]
        latency.append(time.perf_counter() - start)
        r["question"], r["retrieved"] = question, found
        r["hit"] = mentions(found, keyword)
        hits += r["hit"]
        if found:
            precision.append(sum(mentions([v], keyword) for v in found) / len(found))
    noise = {q: [m["value"] for m in profile.retrieve(q, limit=3)] for q in UNRELATED}

    n = len(CASES)
    results = {
        "statements": n,
        "per_category": {c: sum(1 for r in rows if r["category"] == c) for c in ("likes", "dislikes", "facts")},
        "extraction_recall": sum(r["any_category"] for r in rows) / n,
        "extraction_recall_right_category": sum(r["right_category"] for r in rows) / n,
        "extraction_seconds_mean": sum(r["seconds"] for r in rows) / n,
        "retained": sum(r["retained"] for r in rows) / n,
        "stored_per_category": {c: len(v) for c, v in stored.items()},
        "retrieval_hit_rate_at_3": hits / n,
        "retrieval_precision_at_3": sum(precision) / len(precision) if precision else 0.0,
        "retrieval_latency_ms_mean": 1000 * sum(latency) / n,
        "unrelated_questions_retrieving_anything": sum(bool(v) for v in noise.values()) / len(UNRELATED),
        "days_until_unused_memory_forgotten": {str(i): days_until_forgotten(i) for i in (1, 5, 9, 10, 13)},
        "stored": stored,
        "unrelated": noise,
        "cases": rows,
    }
    out = RESULTS_DIR / "memory.json"
    out.write_text(json.dumps(results, indent=2))
    drop_bench_db()

    print(f"\nRetained {results['retained']:.0%} | extraction recall {results['extraction_recall']:.0%} "
          f"({results['extraction_recall_right_category']:.0%} right category) | "
          f"hit@3 {results['retrieval_hit_rate_at_3']:.1%} | precision@3 {results['retrieval_precision_at_3']:.0%} | "
          f"unrelated with results {results['unrelated_questions_retrieving_anything']:.0%}")
    print(f"Forgetting (days, by importance): {results['days_until_unused_memory_forgotten']}")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
    import os
    sys.stdout.flush()
    os._exit(0)
