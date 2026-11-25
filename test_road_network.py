
from services.road_network import (
    load_road_network,
    get_graph_info,
    find_fastest_route
)

print("Loading road network...")

graph = load_road_network()

info = get_graph_info(graph)

print("\nRoad Network Loaded!")
print("Intersections:", info["intersections"])
print("Road segments:", info["road_segments"])

# Test GPS coordinates around Koramangala
origin = (12.9352, 77.6245)
destination = (12.9279, 77.6271)

print("\nFinding fastest emergency route...")

result = find_fastest_route(
    graph,
    origin,
    destination
)

print("\nFASTEST ROUTE FOUND!")
print("Distance:", result["distance_km"], "km")
print("Estimated time:", result["travel_time_minutes"], "minutes")
print("Number of road nodes:", len(result["route"]))
