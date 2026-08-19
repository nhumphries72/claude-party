import json
import math
import heapq

class Navigator:
    def __init__(self, map_file="map_nodes.json"):
        with open(map_file, 'r') as f:
            self.graph_data = json.load(f)
            
        self.nodes = self.graph_data['nodes']
        self.edges = self.graph_data['edges']
        self.vent_edges = self.graph_data['vent_edges']
        
    def _euclidean_distance(self, node_a, node_b):
        x1, y1 = self.nodes[node_a]['x'], self.nodes[node_a]['y']
        x2, y2 = self.nodes[node_b]['x'], self.nodes[node_b]['y']
        return math.hypot(x2 - x1, y2 - y1)
    
    def _build_adjacency_list(self):
        adj = {n: [] for n in self.nodes}
        for u, v in self.edges:
            cost = self._euclidean_distance(u, v)
            adj[u].append((v, cost))
            adj[v].append((u,cost))
        return adj
    
    def is_valid_vent(self, current_node, target_vent):
        connection = [current_node, target_vent]
        reverse = [target_vent, current_node]
        return connection in self.vent_edges or reverse in self.vent_edges
    
    def find_nearest_node(self, x, y):
        closest = None
        min_dist = float('inf')
        for name, coords in self.nodes.items():
            dist = math.hypot(coords['x'] - x, coords['y'] - y)
            if dist < min_dist:
                min_dist = dist
                closest = name
                
        return closest
        
    def find_path(self, start_node, end_node):
        if start_node not in self.nodes or end_node not in self.nodes:
            return []
        
        adj = self._build_adjacency_list()
        queue = [(0, start_node)]
        came_from = {}
        g_score = {n: float('inf') for n in self.nodes}
        g_score[start_node] = 0
        
        while queue:
            current_f, current = heapq.heappop(queue)
            
            if current == end_node:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_node)
                path.reverse()
                return path
            
            # A* algorithm
            for neighbor, weight in adj[current]:
                tentative_g = g_score[current] + weight
                if tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self._euclidean_distance(neighbor, end_node)
                    heapq.heappush(queue, (f_score, neighbor))
            
        return []