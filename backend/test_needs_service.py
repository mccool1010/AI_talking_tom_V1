from needs_service import NeedsService

needs = NeedsService()

print(needs.hunger)
print(needs.sleepiness)
print(needs.social_need)

needs.update_from_conversation()

print(needs.hunger)
print(needs.sleepiness)
print(needs.social_need)