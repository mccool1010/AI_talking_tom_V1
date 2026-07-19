from relationship_service import RelationshipService

relationship = RelationshipService()

print(relationship.trust)
print(relationship.friendship)
print(relationship.attachment)

relationship.update_from_conversation("happy")

print(relationship.trust)
print(relationship.friendship)
print(relationship.attachment)