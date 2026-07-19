# test_like_dislike_importance.py

from profile_memory_service import ProfileMemoryService

profile = ProfileMemoryService()

profile.add_like("Linux Mint")
profile.add_like("Linux Mint")
profile.add_like("Linux Mint")

profile.add_dislike("Windows Updates")
profile.add_dislike("Windows Updates")

print(
    profile.get_profile()
)