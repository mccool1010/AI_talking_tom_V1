from profile_memory_service import ProfileMemoryService

profile = ProfileMemoryService()

print("----- SEARCH TESTS -----")

print(
    profile.search_memories(
        "linux"
    )
)

print(
    profile.search_memories(
        "talking"
    )
)

print(
    profile.search_memories(
        "pizza"
    )
)

print(
    profile.search_memories(
        "machine"
    )
)