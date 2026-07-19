from profile_memory_service import ProfileMemoryService

profile = ProfileMemoryService()

print("===== BEFORE =====")
print(profile.get_profile())

print("\n===== ADDING DUPLICATES =====")

profile.add_fact(
    "Building AI Talking Tom"
)

profile.add_fact(
    "Building AI Talking Tom"
)

profile.add_fact(
    "Building AI Talking Tom"
)

profile.add_like(
    "Linux Mint"
)

profile.add_like(
    "Linux Mint"
)

profile.add_like(
    "Linux Mint"
)

print("\n===== AFTER =====")
print(profile.get_profile())