import fastf1
import fastf1.plotting

session = fastf1.get_session(2024, 'Bahrain', 'R')
session.load()

circuit_info = session.get_circuit_info()

print(circuit_info.corners)