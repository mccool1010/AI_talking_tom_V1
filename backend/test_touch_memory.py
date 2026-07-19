# test_touch_memory.py

from profile_memory_service import ProfileMemoryService

profile = ProfileMemoryService()

print("Before:")
print(profile.get_profile())

print("\nRetrieving...")

profile.get_top_memories("talking")

print("\nAfter:")
print(profile.get_profile())