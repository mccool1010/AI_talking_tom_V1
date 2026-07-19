from profile_memory_service import ProfileMemoryService
from memory_decay_service import MemoryDecayService

profile_service = ProfileMemoryService()
decay = MemoryDecayService()

profile = profile_service.get_profile()

print("===== BEFORE =====")
print(profile)

decay.decay(profile)

decay.remove_forgotten_memories(profile)

print("===== AFTER =====")
print(profile)

decay.save_profile(
    profile,
    profile_service.collection
)