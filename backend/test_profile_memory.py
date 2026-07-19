from profile_memory_service import ProfileMemoryService

profile = ProfileMemoryService()

profile.add_fact(
    "Building AI Talking Tom",
    importance=10
)

profile.add_fact(
    "Ate pizza yesterday",
    importance=2
)

print(
    profile.get_important_facts()
)
print(
    profile.search_memories(
        "linux"
    )
)