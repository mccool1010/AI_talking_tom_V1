from tom_state_service import TomStateService

tom = TomStateService()

print(tom.energy)
print(tom.friendliness)
print(tom.curiosity)

tom.update_energy(-5)
tom.update_friendliness(+10)
tom.update_curiosity(+15)

print(tom.energy)
print(tom.friendliness)
print(tom.curiosity)