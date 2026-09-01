import asyncio
import websockets
import json
import time
import random
from navigator import Navigator
from meeting_manager import MeetingManager
from cli_functions import execute_command
from events import handle_events
from collections import deque

active_connection = None
nav = Navigator()
NODE_MAP = nav.nodes
ROOM_NODES = nav.rooms
with open("task_info.json", 'r') as task_info: TASK_INFO = json.load(task_info)

bots, vents, bot_arrival_events, active_actions, MASTER_TASKS = {}, {}, {}, {}, {}
cooldowns = { "kill": {}, "sabotage": {} }
bot_memories = {i: deque(maxlen=5) for i in range(15)}
manager = MeetingManager(active_connection, bots, active_actions, bot_arrival_events)

async def handle_game_state(websocket):
    global active_connection, MASTER_TASKS
    active_connection = websocket
    print(f"Unity client connected")
    time.sleep(0.005)
    
    try:
        async for message in websocket:
            data = json.loads(message)
            
            if data.get('type') == "telemetry":
                players = data.get("players")
                for id, info in players.items():
                    bots[int(id)] = {
                        'position': {"x": info['x'], "y": info['y']},
                        'alive': info['alive'],
                        'visible_players': info.get('visible_players', [])
                    }
                    bots[int(id)]['role'] = "imposter" if info['imposter'] else "crewmate"
            
            elif data.get('type') == "event":
                event_context = {
                    "data": data,
                    "bot_arrival_events": bot_arrival_events,
                    "active_actions": active_actions,
                    "cooldowns": cooldowns,
                    "navigator": nav,
                    "manager": manager,
                    "memory": bot_memories,
                    "find_current_room": find_current_room
                }
                handle_events(event_context)
                
            elif data.get('type') == "init_tasks":
                assignments = data.get("assignments", {})
                print(f"Received {len(assignments)} task lists.")
                
                with open("task_info.json", "r") as f:
                    file_content = f.read().strip()
                    TASK_INFO = json.loads(file_content) if file_content else {}
                    
                    for bot, task_list in assignments.items():
                        MASTER_TASKS[bot] = []
                        for task in task_list:
                            task_name = task['task']
                            
                            if 'location' in task:
                                init_location = [nav.find_nearest_node(task['location']['x'], task['location']['y'])]
                            else:
                                init_location = []
                            
                            if TASK_INFO[task_name]['random']:
                                subsequent_locations = TASK_INFO[task_name]['locations']
                                chosen_locations = random.choices(subsequent_locations, k=2)
                                locations = init_location + chosen_locations
                            else:
                                locations = init_location + TASK_INFO[task_name]['locations']
                            
                            MASTER_TASKS[bot].append({
                                "task": task_name,
                                "duration": TASK_INFO[task_name]['duration'],
                                "locations": locations,
                                "async": TASK_INFO[task_name]['async']
                            })
                            vents[bot] = None
                    
                with open("task_dump.json", "w") as f: json.dump(MASTER_TASKS, f, indent=4)
                
                for bot in assignments.keys():
                    if bots[int(bot)]['role'] == "imposter":
                        cooldowns['kill'][int(bot)] = time.time() + 10
                        cooldowns['sabotage'][int(bot)] = time.time() + 10
                            
            elif data.get('type') == "location":
                print(data.get("current_location"))
    
    except websockets.exceptions.ConnectionClosed:
        print(f"Unity client disconnected")
        time.sleep(0.005)
        
async def traverse_path(bot_id, target_node):
    try:
        if not bots[bot_id]['position']:
            print(f"Cannot route bot {bot_id}")
            return
        
        current_x, current_y = bots[bot_id]['position']['x'], bots[bot_id]['position']['y']
        start_node = nav.find_nearest_node(current_x, current_y)
        
        print(f"Calculating path from {start_node} to {target_node}")
        
        path = nav.find_path(start_node, target_node)
        if not path:
            print(f"Navigation error: no path found to {target_node}")
            return
        
        if bot_id not in bot_arrival_events: bot_arrival_events[bot_id] = asyncio.Event()
        
        seen_bots = set()
        
        for step, node in enumerate(path):
            target_x, target_y = nav.nodes[node]['x'], nav.nodes[node]['y']
            
            bot_arrival_events[bot_id].clear()
            
            payload = {
                "type": "command",
                "action": "move",
                "bot_id": bot_id,
                "x": target_x,
                "y": target_y
            }
            
            await active_connection.send(json.dumps(payload))
            await bot_arrival_events[bot_id].wait()
            
            visible_bots = bots[bot_id].get('visible_players')
            for seen_id in visible_bots: seen_bots.add(str(seen_id))

        print(f"Bot {bot_id} reached destination {target_node}")
    
    except asyncio.CancelledError:
        pass
    
def find_current_room(bot_id):
    bot_pos = bots[bot_id]["position"]
    current_node = nav.find_nearest_node(bot_pos["x"], bot_pos["y"])
    room_key = next(k for k in nav.rooms if current_node in k)
    return room_key
        
async def cli():
    global NODE_MAP, TASK_INFO, MASTER_TASKS
    loop = asyncio.get_running_loop()
    
    while True:
        cmd = await loop.run_in_executor(None, input, "")
        if not cmd: continue
        
        parts = cmd.split()
        command = parts.pop(0)
        context = {
            "active_connection": active_connection,
            "active_actions": active_actions,
            "MASTER_TASKS": MASTER_TASKS,
            "traverse_path": traverse_path,
            "bots": bots,
            "bot_arrival_events": bot_arrival_events,
            "cooldowns": cooldowns,
            "navigator": nav,
            "bots": bots,
            "vents": vents,
            "ROOM_NODES": ROOM_NODES,
            "bot_memories": bot_memories
        }
        
        await execute_command(command, parts, context)
                    
async def main():
    
    server = websockets.serve(handle_game_state, "localhost", 8765)
    print("Moderator listening on ws://localhost:8765")
        
    await asyncio.gather(
        server,
        cli()
    )
        
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        exit