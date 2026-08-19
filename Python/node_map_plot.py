import json
import math
import matplotlib.pyplot as plt

MAP_FILE = "map_nodes.json"

try:
    with open(MAP_FILE, 'r') as f:
        raw_data = json.load(f)
except FileNotFoundError:
    exit()
    
graph = {"nodes": raw_data['nodes'], "edges": raw_data['edges'], "vent_edges": raw_data['vent_edges']}
    
nodes = graph["nodes"]
edges = graph["edges"]
vent_edges = graph["vent_edges"]

fig, ax = plt.subplots(figsize=(10, 8))
plt.title("Cartography Tool")
ax.set_aspect("equal")
ax.grid(True, linestyle='--', alpha=0.6)

x_vals = [n['x'] for n in nodes.values()]
y_vals = [n['y'] for n in nodes.values()]

ax.scatter(x_vals, y_vals, zorder=5, c='blue')
for name, coords in nodes.items():
    ax.annotate(name, (coords['x'], coords['y']), xytext=(5, 5), textcoords='offset points', fontsize=8)

for edge in edges:
    if edge[0] in nodes and edge[1] in nodes:
        x0, y0 = nodes[edge[0]]['x'], nodes[edge[0]]['y']
        x1, y1 = nodes[edge[1]]['x'], nodes[edge[1]]['y']
        ax.plot([x0, x1], [y0, y1], 'k-', zorder=1)
        
for edge in vent_edges:
    if edge[0] in nodes and edge[1] in nodes:
        x0, y0 = nodes[edge[0]]['x'], nodes[edge[0]]['y']
        x1, y1 = nodes[edge[1]]['x'], nodes[edge[1]]['y']
        ax.plot([x0, x1], [y0, y1], 'r--', zorder=1)
        
selected_node = None
current_mode = "walk"

def get_closest_node(x, y):
    closest = None
    min_dist = float('inf')
    for name, coords in nodes.items():
        dist = math.hypot(coords['x'] - x, coords['y'] - y)
        if dist < min_dist:
            min_dist = dist
            closest = name
            
    if min_dist < 0.75: return closest

    return None

def on_click(event):
    global selected_node
    
    if event.xdata is None or event.ydata is None: return
    
    clicked = get_closest_node(event.xdata, event.ydata)
    if not clicked: return
    
    if selected_node is None:
        selected_node = clicked
        print(f"Selected: {selected_node}")
    else:
        if selected_node != clicked:
            new_edge = [selected_node, clicked]
            reverse_edge = [clicked, selected_node]
            
            target_list = edges if current_mode == "walk" else vent_edges
            
            if new_edge not in edges and reverse_edge not in edges:
                target_list.append(new_edge)
                
                x0, y0 = nodes[selected_node]['x'], nodes[selected_node]['y']
                x1, y1 = nodes[clicked]['x'], nodes[clicked]['y']
                ax.plot([x0, x1], [y0, y1], 'r-', zorder=1)
                fig.canvas.draw()
                
                with open(MAP_FILE, 'w') as f:
                    json.dump(graph, f, indent=4)
                    
                print(f"Connected: {selected_node} <-> {clicked}")
                
        selected_node = None
        
def on_key(event):
    global current_mode
    if event.key == 'w':current_mode = "walk"
    elif event.key == 'v': current_mode = "vent"
    print(f"Set mode to {current_mode}")
        
fig.canvas.mpl_connect('button_press_event', on_click)
fig.canvas.mpl_connect('key_press_event', on_key)
plt.show()