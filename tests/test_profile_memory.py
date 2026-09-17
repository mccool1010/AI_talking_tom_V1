from profile_memory_service import ProfileMemoryService, is_duplicate, keywords


def values(service, category):
    return [m["value"] for m in service.get_profile()[category]]


def test_new_likes_and_dislikes_are_saved(user):
    p = ProfileMemoryService(user)
    p.add_like("football")
    p.add_dislike("spicy food")
    p.add_fact("Studies computer science")
    assert values(p, "likes") == ["football"]
    assert values(p, "dislikes") == ["spicy food"]
    assert values(p, "facts") == ["Studies computer science"]


def test_second_like_is_saved_after_the_first(user):
    p = ProfileMemoryService(user)
    p.add_like("football")
    p.add_like("jazz music")
    assert values(p, "likes") == ["football", "jazz music"]


def test_duplicate_reinforces_instead_of_adding(user):
    p = ProfileMemoryService(user)
    p.add_fact("Sister lives in Bangalore")
    p.add_fact("sister lives in bangalore.")
    p.add_fact("Sister lives in Bangalore!")
    facts = p.get_profile()["facts"]
    assert len(facts) == 1
    assert facts[0]["importance"] == 7


def test_near_duplicates_detected_but_different_facts_kept():
    assert is_duplicate("Building a robot for college project",
                        "Building a robot for the college project")
    assert not is_duplicate("Drives a red Honda", "Drives a blue Toyota")


def test_blank_values_ignored(user):
    p = ProfileMemoryService(user)
    p.add_like("   ")
    p.add_fact("")
    assert values(p, "likes") == [] and values(p, "facts") == []


def test_keywords_drop_stopwords_and_stem():
    assert keywords("I am going to play with my robots today") == {"play", "robot"}


def test_retrieve_matches_whole_words_ranked_by_overlap(user):
    p = ProfileMemoryService(user)
    p.add_fact("Training for a marathon")
    p.add_fact("Building a robot for college project")
    p.add_fact("Moved to Chennai last year")
    p.add_like("college football")

    got = [m["value"] for m in p.retrieve("The robot for my college project finally moved!")]
    assert got[0] == "Building a robot for college project"
    # "rain" must not match "Training" the way substring search did
    assert p.retrieve("It looks like rain") == []


def test_retrieve_ignores_filler_questions(user):
    p = ProfileMemoryService(user)
    for fact in ["My name is Hari", "Working part-time at a coffee shop", "I am a student"]:
        p.add_fact(fact)
    for query in ["What time is it?", "Tell me a joke.", "How is the weather?", "I am tired."]:
        assert p.retrieve(query) == [], query


def test_retrieve_touches_only_returned_memories(user):
    p = ProfileMemoryService(user)
    p.add_fact("Plays guitar")
    p.add_fact("Plays piano")
    for m in p.get_profile()["facts"]:
        p.collection.update_one({"owner": user.user_id, "facts.value": m["value"]},
                                {"$set": {"facts.$.last_accessed": "2000-01-01T00:00:00"}})
    p.retrieve("my guitar is out of tune", limit=1)
    accessed = {m["value"]: m["last_accessed"] for m in p.get_profile()["facts"]}
    assert accessed["Plays piano"] == "2000-01-01T00:00:00"
    assert accessed["Plays guitar"] != "2000-01-01T00:00:00"


def test_profiles_are_per_user(user):
    p = ProfileMemoryService(user)
    p.add_like("chess")
    p.switch_user("bob")
    assert values(p, "likes") == []
    p.add_like("tennis")
    p.switch_user("alice")
    assert values(p, "likes") == ["chess"]
