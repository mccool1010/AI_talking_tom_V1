from internal_thought_service import InternalThoughtService

thoughts = InternalThoughtService()

result = thoughts.generate(
    energy=20,
    hunger=80,
    sleepiness=75,
    social_need=85,
    relationship={
        "trust":90,
        "attachment":92
    },
    memories=[
        "Building AI Talking Tom"
    ]
)

print(result)