import json
import asyncio
import time

with open("map_nodes.json", 'r') as node_map:
    ROOM_NODES = json.load(node_map).get("room_nodes")

fix_nodes = {
    "admin": "admin_oxygen",
    "o2": "o2_restore",
    "top": "reactor_sabotage_north",
    "bottom": "reactor_sabotage_south",
    "lights": "electrical_lights",
    "comms": "communications_sabotage"
}

async def begin(parts, context):
    active_connection = context.get('active_connection')
    cooldowns = context.get('cooldowns')
    
    bot_id = int(parts[0])
    system = parts[1]
    room = parts[2] if len(parts) > 2 else None
    
    if bot_id in cooldowns['sabotage']:
        if time.time() < cooldowns['sabotage'][bot_id]:
            remaining = int(cooldowns['sabotage'][bot_id] - time.time())
            print(f"Bot {bot_id} cannot perform another sabotage for {remaining} seconds")
            return
        else:
            del cooldowns['sabotage'][bot_id]

    payload = {
        "type": "command",
        "action": "sabotage",
        "sub_action": "start",
        "system": system,
        "bot_id": bot_id,
        "room": room
    }
    await active_connection.send(json.dumps(payload))
    
async def fix(parts, context):
    active_actions = context.get('active_actions')
    
    bot_id = int(parts[0])
    system = parts[1]
    panel = parts[2] if len(parts) > 2 else None
    
    print(f"Dispatching bot {bot_id} to fix {system}")
    
    active_actions[bot_id] = asyncio.create_task(run_fix_sequence(bot_id, system, panel, context))
    
async def run_fix_sequence(bot_id, system, panel, context):
    active_connection = context.get('active_connection')
    traverse_path = context.get('traverse_path')
    active_actions = context.get('active_actions')
    
    try:
        if panel:
            await traverse_path(bot_id, fix_nodes[panel])
        else:
            await traverse_path(bot_id, fix_nodes[system.lower()])
        await asyncio.sleep(3)
        
        payload = {
            "type": "command",
            "action": "sabotage",
            "sub_action": "fix",
            "system": system,
            "bot_id": bot_id,
            "panel": panel
        }
        await active_connection.send(json.dumps(payload))
        print(f"bot {bot_id} successfully repaired {system}")
    
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s repair sequence was interrupted")
        raise
    
    finally:
        if bot_id in active_actions:
            del active_actions[bot_id]
            
async def lock_doors(room, nav):

    if room not in ROOM_NODES:
        print(f"Cannot find {room} room")
        return
    
    locked_nodes = set(ROOM_NODES[room])
    severed_edges = []
    
    for edge in nav.edges:
        if (edge[0] in locked_nodes) ^ (edge[1] in locked_nodes):
            severed_edges.append(edge)
    
    nav.edges = [edge for edge in nav.edges if edge not in severed_edges]
    
    print(f"Doors to room {room} locked. Severed {len(severed_edges)} connections")
    
    try:
        await asyncio.sleep(10)
    finally:
        nav.edges.extend(severed_edges)
        print(f"Doors to room {room} unlocked. Restored {len(severed_edges)} connections")        
    
        