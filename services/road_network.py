
import osmnx as ox
import networkx as nx
import math


def load_road_network(patient_lat, patient_lon):
    """
    Dynamically download the driving road network
    around the patient's actual GPS location.
    """

    print("Loading road network around patient location...")

    graph = ox.graph_from_point(
        center_point=(patient_lat, patient_lon),
        dist=7000,
        network_type="drive",
        simplify=True,
        retain_all=False
    )

    if graph.number_of_edges() == 0:
        raise ValueError(
            "No driving roads found around this location."
        )

    graph = ox.add_edge_speeds(graph)
    graph = ox.add_edge_travel_times(graph)

    print(
        f"Road network loaded: "
        f"{graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges."
    )

    return graph


def get_graph_info(graph):

    return {
        "intersections": graph.number_of_nodes(),
        "road_segments": graph.number_of_edges()
    }


def calculate_route_metrics(graph, route):

    """
    Calculate road distance and travel time directly
    from the road network.
    """

    total_distance = 0
    total_time = 0

    for u, v in zip(route[:-1], route[1:]):

        edge_data = graph.get_edge_data(u, v)

        if not edge_data:
            raise nx.NetworkXNoPath(
                f"No road edge between {u} and {v}"
            )

        best_edge = min(
            edge_data.values(),
            key=lambda edge: float(
                edge.get("travel_time", float("inf"))
            )
        )

        total_distance += float(
            best_edge.get("length", 0)
        )

        total_time += float(
            best_edge.get("travel_time", 0)
        )

    return {
        "distance_km": round(total_distance / 1000, 2),
        "travel_time_minutes": round(total_time / 60, 2)
    }


def find_fastest_route(graph, origin, destination):
    """
    Find the fastest driving route between two GPS locations.

    origin and destination must be (latitude, longitude).
    """

    origin_node = ox.distance.nearest_nodes(
        graph,
        X=origin[1],
        Y=origin[0]
    )

    destination_node = ox.distance.nearest_nodes(
        graph,
        X=destination[1],
        Y=destination[0]
    )

    # Find shortest route based on estimated travel time
    route = nx.shortest_path(
        graph,
        origin_node,
        destination_node,
        weight="travel_time"
    )

    # Handle patient and hospital snapping to the same node
    if len(route) < 2:

        from geopy.distance import geodesic

        distance_km = geodesic(
            origin,
            destination
        ).km

        return {
            "route": route,
            "distance_km": round(distance_km, 2),
            "travel_time_minutes": round(
                (distance_km / 30) * 60, 2
            )
        }

    metrics = calculate_route_metrics(
        graph,
        route
    )

    return {
        "route": route,
        "distance_km": metrics["distance_km"],
        "travel_time_minutes": metrics["travel_time_minutes"]
    }
