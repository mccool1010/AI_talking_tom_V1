from profile_memory_service import ProfileMemoryService

profile = ProfileMemoryService()

print(
    profile.get_top_memories(
        "talking"
    )
)