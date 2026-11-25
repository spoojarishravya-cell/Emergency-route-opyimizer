
from services.road_network import load_road_network
from services.hospital_finder import find_nearby_hospitals

print("Loading road network...")

graph = load_road_network()

print("Searching for nearby hospitals...")

hospitals = find_nearby_hospitals(
    graph,
    patient_lat=12.9352,
    patient_lon=77.6245
)

if hospitals:

    print("\nNEARBY HOSPITALS FOUND!")

    for index, hospital in enumerate(hospitals, start=1):

        print(f"\nHospital {index}: {hospital['name']}")
        print("Distance:", hospital["distance_km"], "km")
        print(
            "Travel time:",
            hospital["travel_time_minutes"],
            "minutes"
        )

else:
    print("No reachable hospitals found.")
