
import networkx as nx

from services.pathfinding import bfs, ucs, astar


# Create a small directed road network
graph = nx.MultiDiGraph()

# Add intersections
graph.add_node(1, x=77.5900, y=12.9700)
graph.add_node(2, x=77.5910, y=12.9700)
graph.add_node(3, x=77.5920, y=12.9700)
graph.add_node(4, x=77.5900, y=12.9710)

# Add roads with distance and travel time
graph.add_edge(1, 2, length=100, travel_time=10)
graph.add_edge(2, 3, length=100, travel_time=10)

graph.add_edge(1, 4, length=150, travel_time=5)
graph.add_edge(4, 3, length=150, travel_time=5)

source = 1
destination = 3

print("\nBFS Route:", bfs(graph, source, destination))
print("UCS Route:", ucs(graph, source, destination))
print("A* Route:", astar(graph, source, destination))
