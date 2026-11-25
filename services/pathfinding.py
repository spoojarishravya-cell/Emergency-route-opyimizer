
import heapq
import itertools
import math


def get_edge_cost(graph, u, v, weight="travel_time"):
    """
    Return the minimum cost among parallel directed road edges.
    OSMnx uses a MultiDiGraph, so multiple roads may connect
    the same pair of intersections.
    """
    edge_data = graph.get_edge_data(u, v)

    if not edge_data:
        raise ValueError(f"No road connection between {u} and {v}")

    costs = []

    for edge in edge_data.values():
        cost = float(edge[weight])

        if not math.isfinite(cost) or cost < 0:
            raise ValueError(f"Invalid {weight} on edge {u} -> {v}")

        costs.append(cost)

    return min(costs)


def bfs(graph, source, destination):
    """
    Breadth-First Search.
    Finds a route with the fewest road segments.
    It does NOT minimize travel time.
    """
    if source not in graph or destination not in graph:
        return None

    queue = [source]
    visited = {source}
    parent = {}

    while queue:
        current = queue.pop(0)

        if current == destination:
            break

        for neighbor in graph.successors(current):
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = current
                queue.append(neighbor)

    if destination not in visited:
        return None

    route = [destination]

    while route[-1] != source:
        route.append(parent[route[-1]])

    return route[::-1]


def ucs(graph, source, destination, weight="travel_time"):
    """
    Uniform Cost Search.
    Finds the route with minimum cumulative travel cost.
    With non-negative edge costs, this is equivalent to Dijkstra.
    """
    if source not in graph or destination not in graph:
        return None

    counter = itertools.count()
    priority_queue = [(0.0, next(counter), source)]

    distances = {source: 0.0}
    parent = {}
    visited = set()

    while priority_queue:
        current_cost, _, current = heapq.heappop(priority_queue)

        if current in visited:
            continue

        visited.add(current)

        if current == destination:
            break

        for neighbor in graph.successors(current):
            if neighbor in visited:
                continue

            edge_cost = get_edge_cost(
                graph, current, neighbor, weight
            )

            new_cost = current_cost + edge_cost

            if new_cost < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_cost
                parent[neighbor] = current

                heapq.heappush(
                    priority_queue,
                    (new_cost, next(counter), neighbor)
                )

    if destination not in distances:
        return None

    route = [destination]

    while route[-1] != source:
        route.append(parent[route[-1]])

    return route[::-1]


def haversine_distance(node_a, node_b):
    """
    Calculate straight-line distance in metres using
    the latitude and longitude stored in OSMnx nodes.
    """
    lat1 = math.radians(node_a["y"])
    lon1 = math.radians(node_a["x"])
    lat2 = math.radians(node_b["y"])
    lon2 = math.radians(node_b["x"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 6371000 * 2 * math.asin(
        min(1.0, math.sqrt(a))
    )


def calculate_min_cost_per_metre(graph, weight="travel_time"):
    """
    Find a safe lower bound for travel cost per metre.

    If any edge has invalid or zero length, use zero as a
    conservative heuristic factor.
    """
    minimum_ratio = float("inf")

    for _, _, _, data in graph.edges(keys=True, data=True):
        try:
            length = float(data["length"])
            cost = float(data[weight])

            if (
                not math.isfinite(length)
                or not math.isfinite(cost)
                or length <= 0
                or cost < 0
            ):
                return 0.0

            minimum_ratio = min(
                minimum_ratio,
                cost / length
            )

        except (KeyError, TypeError, ValueError):
            return 0.0

    if minimum_ratio == float("inf"):
        return 0.0

    return minimum_ratio


def astar(graph, source, destination, weight="travel_time"):
    """
    A* Search.
    Finds a minimum-travel-cost route using:
        f(n) = g(n) + h(n)

    g(n): cost from source to current node.
    h(n): estimated minimum remaining travel cost.

    The heuristic uses straight-line distance multiplied
    by a safe minimum travel-cost-per-metre factor.
    """
    if source not in graph or destination not in graph:
        return None

    minimum_ratio = calculate_min_cost_per_metre(
        graph, weight
    )

    def heuristic(node):
        try:
            distance = haversine_distance(
                graph.nodes[node],
                graph.nodes[destination]
            )

            return distance * minimum_ratio

        except (KeyError, TypeError, ValueError):
            return 0.0

    counter = itertools.count()

    priority_queue = [
        (heuristic(source), next(counter), 0.0, source)
    ]

    distances = {source: 0.0}
    parent = {}
    visited = set()

    while priority_queue:
        _, _, current_cost, current = heapq.heappop(
            priority_queue
        )

        if current in visited:
            continue

        visited.add(current)

        if current == destination:
            break

        for neighbor in graph.successors(current):
            if neighbor in visited:
                continue

            edge_cost = get_edge_cost(
                graph, current, neighbor, weight
            )

            new_cost = current_cost + edge_cost

            if new_cost < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_cost
                parent[neighbor] = current

                estimated_total = (
                    new_cost + heuristic(neighbor)
                )

                heapq.heappush(
                    priority_queue,
                    (
                        estimated_total,
                        next(counter),
                        new_cost,
                        neighbor
                    )
                )

    if destination not in distances:
        return None

    route = [destination]

    while route[-1] != source:
        route.append(parent[route[-1]])

    return route[::-1]
