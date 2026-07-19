from relationship_prompt_service import RelationshipPromptService

relationship_prompt = RelationshipPromptService()

print("=" * 40)
print("LOW RELATIONSHIP")
print("=" * 40)

print(
    relationship_prompt.build(
        trust=20,
        friendship=20,
        attachment=20
    )
)

print("\n" + "=" * 40)
print("MEDIUM RELATIONSHIP")
print("=" * 40)

print(
    relationship_prompt.build(
        trust=50,
        friendship=55,
        attachment=60
    )
)

print("\n" + "=" * 40)
print("HIGH RELATIONSHIP")
print("=" * 40)

print(
    relationship_prompt.build(
        trust=90,
        friendship=85,
        attachment=95
    )
)