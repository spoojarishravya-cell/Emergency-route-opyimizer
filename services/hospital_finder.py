from functools import lru_cache

import networkx as nx
import osmnx as ox
from geopy.distance import geodesic


@lru_cache(maxsize=128)
def _get_hospital_locations(latitude_key, longitude_key):
    """Cache hospital coordinates so Overpass is not queried on every click."""
    tags = {"amenity": "hospital", "healthcare": "hospital"}
    features = ox.features_from_point(
        center_point=(latitude_key, longitude_key),
        tags=tags,
        dist=2500
    )
    if features.empty:
        return tuple()

    locations = []
    visited = set()
    for _, hospital in features.iterrows():
        geometry = hospital.geometry
        if geometry is None or geometry.is_empty:
            continue

        point = geometry.representative_point()
        latitude, longitude = float(point.y), float(point.x)

        name = hospital.get("name")
        if name is None or str(name) == "nan":
            name = hospital.get("name:en")
        if name is None or str(name) == "nan":
            name = "Unnamed Hospital"

        key = (str(name), round(latitude, 5), round(longitude, 5))
        if key not in visited:
            visited.add(key)
            locations.append((str(name), latitude, longitude))

    return tuple(locations)


def calculate_route_metrics(
    graph, route, patient_lat, patient_lon, hospital_lat, hospital_lon
):
    """Calculate distance/time from road edges, with a same-node fallback."""
    if len(route) < 2:
        distance_km = geodesic(
            (patient_lat, patient_lon), (hospital_lat, hospital_lon)
        ).km
        return round(distance_km, 2), round((distance_km / 30) * 60, 2)

    total_distance = 0.0
    total_travel_time = 0.0
    for u, v in zip(route[:-1], route[1:]):
        edge_data = graph.get_edge_data(u, v)
        if not edge_data:
            raise nx.NetworkXNoPath(f"No road connection between {u} and {v}")

        best_edge = min(
            edge_data.values(),
            key=lambda data: float(data.get("travel_time", float("inf")))
        )
        total_distance += float(best_edge.get("length", 0))
        total_travel_time += float(best_edge.get("travel_time", 0))

    return round(total_distance / 1000, 2), round(total_travel_time / 60, 2)


def find_nearby_hospitals(graph, patient_lat, patient_lon):
    """
    Discover nearby hospitals and rank by estimated driving time.
    One Dijkstra run serves every hospital in the discovered set.
    """
    if graph is None or graph.number_of_edges() == 0:
        raise ValueError("Road network is empty or contains no edges.")

    latitude_key = round(float(patient_lat), 3)
    longitude_key = round(float(patient_lon), 3)
    hospital_locations = _get_hospital_locations(latitude_key, longitude_key)
    if not hospital_locations:
        return []

    try:
        patient_node = ox.distance.nearest_nodes(
            graph, X=patient_lon, Y=patient_lat
        )
    except Exception as error:
        raise ValueError(
            "Could not find a nearby road for the patient location. "
            "Check whether the road network covers this area."
        ) from error

    # Compute all fastest paths from the patient once, rather than once per hospital.
    _, paths = nx.single_source_dijkstra(
        graph, patient_node, weight="travel_time"
    )

    results = []
    for name, latitude, longitude in hospital_locations:
        try:
            hospital_node = ox.distance.nearest_nodes(
                graph, X=longitude, Y=latitude
            )
            route = paths.get(hospital_node)
            if route is None:
                continue

            distance_km, travel_time_minutes = calculate_route_metrics(
                graph, route, patient_lat, patient_lon, latitude, longitude
            )
            results.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "distance_km": distance_km,
                "travel_time_minutes": travel_time_minutes,
                "route": route
            })
        except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError):
            continue

    results.sort(key=lambda hospital: hospital["travel_time_minutes"])
    return results
