import json
import asyncio
import time

fix_nodes = {
    "admin": "admin_oxygen",
    "o2": "o2_restore",
    "top": "reactor_sabotage_north",
    "bottom": "reactor_sabotage_south",
    "lights": "electrical_lights",
    "comms": "communications_sabotage"
}

async def begin(parts, context):
    if context.get('active_sabotage')['system'] is not None: return
    
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
    context['active_sabotage']['system'] = system
    
async def fix(parts, context):
    active_actions = context.get('active_actions')
    
    bot_id = int(parts[0])
    system = parts[1]
    panel = parts[2] if len(parts) > 2 else None
    
    print(f"Dispatching bot {bot_id} to fix {system}")
    
    active_actions[bot_id] = asyncio.create_task(run_fix_sequence(bot_id, system, panel, context))
    context.get('sabotage_being_fixed').append((system, panel))
    
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
        context['active_sabotage']['system'] = None
    
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s repair sequence was interrupted")
        raise
    
    finally:
        if bot_id in active_actions:
            del active_actions[bot_id]
            
async def lock_doors(room, nav):

    if room not in nav.nodes:
        print(f"Cannot find {room} room")
        return
    
    locked_nodes = set(nav.nodes[room])
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


VENT_IDS = {
    "admin_vent": 0,
    "cafeteria_vent": 2,
    "navigation_vent_south": 13,
    "navigation_vent_north": 12,
    "weapons_vent": 7,
    "shields_vent": 10,
    "east_hall_vent": 1,
    "electrical_vent": 3,
    "reactor_south_vent": 8,
    "reactor_north_vent": 11,
    "lower_engine_vent": 9,
    "upper_engine_vent": 4,
    "security_vent": 5,
    "medbay_vent": 6
}
        
async def enter_vent(parts, context):
    active_actions = context.get('active_actions')
    nav = context.get('navigator')
    
    bot_id = int(parts[0])
    room = parts[2]
    specific_vent = parts[3] if len(parts) > 3 else None
    
    room_key = next((k for k in nav.rooms.keys() if k.lower() == room.lower()), None)
    if not room_key:
        print(f"Room {room} not found")
        return
    room_vents = [n for n in nav.rooms[room_key] if "vent" in n]
    
    if len(room_vents) == 0:
        print(f"Room {room_key} has no vents")
        return
    elif len(room_vents) == 1:
        target_node = room_vents[0]
    else:
        if not specific_vent:
            print(f"Room {room_key} has multiple vents. Use 'vent {bot_id} enter {room} north/south'")
            return
        
        target_node = next((n for n in room_vents if specific_vent.lower() in n.lower()), None)
        
        if not target_node:
            print(f"Room {room_key} has no {specific_vent} vent")
            return
        
    active_actions[bot_id] = asyncio.create_task(run_vent_enter_sequence(bot_id, target_node, context))
    
async def run_vent_enter_sequence(bot_id, target_node, context):
    active_connection = context.get('active_connection')
    active_actions = context.get('active_actions')
    traverse_path = context.get('traverse_path')
    vents = context.get('vents')
    
    try:
        vent_id = VENT_IDS[target_node]
        print(f"Bot {bot_id} heading to {target_node} to enter a vent")
        await traverse_path(bot_id, target_node)
        
        payload = {
            "type": "command",
            "action": "vent",
            "sub_action": "enter",
            "bot_id": bot_id,
            "vent_id": vent_id
        }
        
        await active_connection.send(json.dumps(payload))
        if bot_id not in vents: vents[bot_id] = None
        vents[bot_id] = target_node
    
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s vent entry was interrupted")
        raise
    
    finally:
        if bot_id in active_actions: del active_actions[bot_id]
        
async def vent_move(parts, context):
    vents = context.get('vents')
    active_actions = context.get('active_actions')
    nav = context.get('navigator')
    
    bot_id = int(parts[0])
    room = parts[2]
    
    if not vents[bot_id]:
        print(f"Bot {bot_id} is not in a vent")
        return
    
    current_node = vents[bot_id]
    connected_nodes = [
        edge[1] if edge[0] == current_node else edge[0]
        for edge in nav.vent_edges if current_node in edge
    ]
    
    room_key = next((k for k in nav.rooms.keys() if k.lower() == room.lower()), None)
    if not room_key:
        print(f"Room {room} not found")
        return
    room_vents = [n for n in nav.rooms[room_key] if "vent" in n]
    
    if len(room_vents) == 0:
        print(f"Room {room_key} has no vents")
        return
    elif len(room_vents) == 1:
        if room_vents[0] in connected_nodes:
            target_node = room_vents[0]
        else:
            print(f"{room_vents[0]} is not connected to {current_node}")
            return
    else:
        for vent in room_vents:
            if vent in connected_nodes:
                target_node = vent
                break
        
        if not target_node:
            print(f"Room {room_key} has no vents connected to {current_node}")
            return
        
    active_actions[bot_id] = asyncio.create_task(run_vent_movement_sequence(bot_id, target_node, context))
    
async def run_vent_movement_sequence(bot_id, target_node, context):
    active_connection = context.get('active_connection')
    active_actions = context.get('active_actions')
    vents = context.get('vents')
    
    try:
        vent_id = VENT_IDS[target_node]
        print(f"Bot {bot_id} moving to {target_node} through air ducts")
        
        payload = {
            "type": "command",
            "action": "vent",
            "sub_action": "move",
            "bot_id": bot_id,
            "vent_id": vent_id
        }
        
        await active_connection.send(json.dumps(payload))
        vents[bot_id] = target_node
        
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s vent movement was interrupted")
        raise
    
    finally:
        if bot_id in active_actions: del active_actions[bot_id]
        
async def exit_vent(parts, context):
    active_connection = context.get('active_connection')
    vents = context.get('vents')
    
    bot_id = int(parts[0])
    
    current_node = vents[bot_id]
    if not current_node:
        print(f"Bot {bot_id} is not in a vent")
        return
    
    vent_id = VENT_IDS[current_node]
    
    try:
        print(f"Bot {bot_id} exiting vent")
        
        payload = {
            "type": "command",
            "action": "vent",
            "sub_action": "exit",
            "bot_id": bot_id,
            "vent_id": vent_id
        }
        
        await active_connection.send(json.dumps(payload))
        vents[bot_id] = None
    
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s vent exiting was interrupted even though that shouldn't be possible")
        raise
    
    
    
        
    

            
        