from environment_service import EnvironmentService

env = EnvironmentService()

print("Before")
print(env.get_environment())

env.update_person(True)

print("\nAfter Person Detected")
print(env.get_environment())

env.update_person(False)

print("\nAfter Person Left")
print(env.get_environment())