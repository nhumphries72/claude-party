import json
import asyncio
import random
import time
import cli_subfunctions as sub
from navigator import Navigator

with open("map_nodes.json", 'r') as node_map: NODE_MAP = json.load(node_map).get("nodes")
with open("task_info.json", 'r') as task_info: TASK_INFO = json.load(task_info)
nav = Navigator()

def interrupt_bot(bot_ids, context):
    active_actions = context.get('active_actions')
    active_connection = context.get('active_connection')
    
    if bot_ids == 'all': bot_ids = range(0, 15)
    if not isinstance(bot_ids, list): bot_ids = [bot_ids]
    
    for bot in bot_ids:
        if bot in active_actions:
            active_actions[bot].cancel()
            del active_actions[bot]
            
            if active_connection:
                stop_payload = {"type": "command", "action": "stop", "bot_id": bot}
                asyncio.create_task(active_connection.send(json.dumps(stop_payload)))

async def execute_command(cmd, parts, context):
    cmd_dict = {
        "move": move,
        "task": prepare_task,
        "refresh": refresh,
        "meeting": call_meeting,
        "kill": kill_target,
        "roles": print_roles,
        "report": report_body,
        "sabotage": execute_sabotage,
        "fix": fix_sabotage,
        "chat": chat,
        "vote": vote,
        "proceed": proceed,
        "vent": vent
    }
    function = cmd_dict.get(cmd)
    
    if function:
        await function(parts, context)
    else:
        print("Unknown command")

async def move(parts, context):
    active_actions = context.get('active_actions')
    bots = context.get('bots')
    ROOM_NODES = context.get('ROOM_NODES')
    
    bot_id = int(parts[0])
    room_name = parts[1]
    
    room_key = next((k for k in ROOM_NODES.keys() if k.lower() == room_name.lower()), None)
    
    if not room_key:
        print(f"Room '{room_name}' not found")
        return
    
    target_nodes = ROOM_NODES[room_key]
    bot_pos = bots[bot_id]['position']
    current_node = nav.find_nearest_node(bot_pos['x'], bot_pos['y'])
    
    shortest_path = None
    best_node = None
    
    for node in target_nodes:
        path = nav.find_path(current_node, node)
        if path:
            if shortest_path is None or len(path) < len(shortest_path):
                shortest_path = path
                best_node = node
                
    if best_node:
        interrupt_bot(bot_id, context)
        print(f"Bot {bot_id} moving to {best_node}")
        active_actions[bot_id] = asyncio.create_task(run_move_sequence(bot_id, best_node, context))
        
async def run_move_sequence(bot_id, destination, context):
    traverse_path = context.get('traverse_path')
    active_actions = context.get('active_actions')
    bot_memories = context.get('bot_memories')
    narrator = context.get('narrator')
    generate_snapshot = context.get('generate_snapshot')
    
    completed = False
    
    try:
        await traverse_path(bot_id, destination)
        completed = True
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s movement was interrupted")
        bot_memories[bot_id].append(f"Interrupted while moving to {destination}")
        raise 
    finally:
        if bot_id in active_actions: del active_actions[bot_id]
        
        if completed and narrator and generate_snapshot:
            state = generate_snapshot(bot_id)
            asyncio.create_task(
                narrator.generate_action(
                    bot_id=bot_id,
                    state=state,
                    event_type="arrived",
                    event_kwargs={"current_room": state.get('current_room')}
                )
            )
        
async def prepare_task(parts, context):
    MASTER_TASKS = context.get('MASTER_TASKS')
    active_actions = context.get('active_actions')
    
    try:
        bot_id = int(parts[0])
        task_index = int(parts[1])
        
        if str(bot_id) not in MASTER_TASKS:
            print(f"No task list for bot {bot_id}")
            return
        
        bot_itinerary = MASTER_TASKS[str(bot_id)]
        
        if task_index < 1 or task_index >= len(bot_itinerary)+1:
            print(f"Invalid index. Bot {bot_id} has {len(bot_itinerary)} tasks assigned.")
            return
            
        task_obj = bot_itinerary[task_index-1]
        task_name = task_obj.get('task')
        
        if len(task_obj['locations']) == 0:
            print(f"Bot {bot_id} has already completed {task_name}")
            return
        
        location = task_obj.get('locations')[0]
        
        if 'cooldown_until' in task_obj and task_obj['cooldown_until'] > time.time():
            remaining = int(task_obj['cooldown_until'] - time.time())
            print(f"Bot {bot_id}'s sample is not ready yet. Will be ready in {remaining} seconds.")
            return
        
        if not location:
            print(f"No target node found for {task_name}")
            return
        
        interrupt_bot(bot_id, context)
        
        active_actions[bot_id] = asyncio.create_task(run_task_sequence(bot_id, task_index, task_obj, location, context))
    
    except ValueError as e:
        print(f"ValueError: {e}")
        

async def run_task_sequence(bot_id, task_index, task_obj, location, context):
    active_connection = context.get('active_connection')
    MASTER_TASKS = context.get('MASTER_TASKS')
    traverse_path = context.get('traverse_path')
    active_actions = context.get('active_actions')
    task_name = task_obj.get('task')
    bot_memories = context.get('bot_memories')
    bots = context.get('bots')
    narrator = context.get('narrator')
    bots = context.get('bots')
    generate_snapshot = context.get('generate_snapshot')
    
    event = None
    
    try:
        print(f"Bot {bot_id} heading to {location} to complete task {task_name}")
        await traverse_path(bot_id, location)
        
        print(f"Bot {bot_id} beginning task {task_name}")
        duration = random.uniform(task_obj['duration'][0], task_obj['duration'][1])
        
        await asyncio.sleep(duration)
        
        if bots[bot_id]['role'] == "imposter":
            event = "task_faked"
            return
        
        MASTER_TASKS[str(bot_id)][task_index-1]['locations'].pop(0)
        
        if len(MASTER_TASKS[str(bot_id)][task_index-1]['locations']) == 0:
            payload = {
                "type": "command",
                "action": "complete_task",
                "bot_id": bot_id,
                "task_name": task_name
            }
            await active_connection.send(json.dumps(payload))
            print(f"Bot {bot_id} fully completed {task_name}")
            MASTER_TASKS[str(bot_id)].pop(task_index - 1)
            event = "task_complete"
        elif task_obj.get('async'):
            task_obj['cooldown_until'] = time.time() + 60
            print(f"Bot {bot_id}'s sample will be ready in one minute")
            bot_memories[bot_id].append("Began sample inspection")
            event = "task_progress"
        else:
            print(f"Bot {bot_id} progressed task {task_name}")
            event = "task_progress"
            bot_memories[bot_id].append(f"Completed stage of task {task_name}")
            
        with open("task_dump.json", "w") as f:
            json.dump(MASTER_TASKS, f, indent=4)
    
    except asyncio.CancelledError:
        print(f"Bot {bot_id}'s task {task_name} was interrupted")
        bot_memories[bot_id].append(f"Interrupted during task {task_name}")
        raise
    
    finally:
        if bot_id in active_actions: del active_actions[bot_id]
        
        if event and narrator and generate_snapshot:
            state = generate_snapshot(bot_id)
            asyncio.create_task(
                narrator.generate_action(
                    bot_id=bot_id,
                    state=state,
                    event_type=event,
                    event_kwargs={"task_name": task_name}
                )
            )
        
async def refresh(parts, context):
    global NODE_MAP, TASK_INFO, MASTER_TASKS
    try:
        with open("map_nodes.json", 'r') as node_map: NODE_MAP = json.load(node_map).get("nodes")
        with open("task_info.json", 'r') as info: TASK_INFO = json.load(info)
        with open("task_dump.json", 'r') as dump: MASTER_TASKS = json.load(dump)
    except Exception as e:
        print(f"Failed to reload: {e}")
                
async def call_meeting(parts, context):
    bot_id = int(parts[0])
    active_actions = context.get('active_actions')
    active_connection = context.get('active_connection')
    traverse_path = context.get('traverse_path')
    bot_memories = context.get('bot_memories')
    
    print(f"Bot {bot_id} preparing to call an emergency meeting")
    
    try:
        nav_task = asyncio.create_task(traverse_path(bot_id, "emergency_table_south"))
        active_actions[bot_id] = nav_task
        await nav_task
        
        payload = {"type": "command", "action": "call_meeting", "bot_id": bot_id}
        await active_connection.send(json.dumps(payload))
        
        other_bots = [b for b in context.get('MASTER_TASKS').keys() if b != bot_id]
        interrupt_bot(other_bots, context)
    except asyncio.CancelledError:
        print(f"Bot {bot_id} interrupted from calling meeting")
        bot_memories[bot_id].append("Interrupted while moving to call a meeting")
        raise
    finally:
        if bot_id in active_actions: del active_actions[bot_id]
        
async def kill_target(parts, context):
    active_actions = context.get('active_actions')
    bots= context.get('bots')
    cooldowns = context.get('cooldowns')
        
    
    imposter_id = int(parts[0])
    victim_id = int(parts[1])
    
    if bots[imposter_id]['role'] == "crewmate" or bots[victim_id]['role'] == "imposter":
        print("Invalid kill command")
        return
    
    if imposter_id in cooldowns['kill']:
        if time.time() < cooldowns['kill'][imposter_id]:
            remaining = int(cooldowns['kill'][imposter_id] - time.time())
            print(f"Bot {imposter_id} cannot perform another kill for {remaining} seconds")
            return
        else:
            del cooldowns['kill'][imposter_id]
    
    interrupt_bot(imposter_id, context)
    print(f"Bot {imposter_id} preparing to kill bot {victim_id}")
    
    active_actions[imposter_id] = asyncio.create_task(run_hunt_sequence(imposter_id, victim_id, context))
    
async def run_hunt_sequence(imposter_id, victim_id, context):
    active_connection = context.get('active_connection')
    active_actions = context.get('active_actions')
    bots = context.get('bots')
    traverse_path = context.get('traverse_path')
    bot_memories = context.get('bot_memories')
    
    try:
        while True:
            if not bots[imposter_id]['position'] or not bots[victim_id]['position']:
                print("Lost track of bots")
                break
            
            imposter_node = nav.find_nearest_node(bots[imposter_id]['position']['x'], bots[imposter_id]['position']['y'])
            victim_node = nav.find_nearest_node(bots[victim_id]['position']['x'], bots[victim_id]['position']['y'])
            
            if imposter_node == victim_node:
                payload = {
                    "type": "command",
                    "action": "hunt",
                    "bot_id": imposter_id,
                    "target_id": victim_id
                }
                await active_connection.send(json.dumps(payload))
                break
            else:
                await traverse_path(imposter_id, victim_node)
    except asyncio.CancelledError:
        print(f"Bot {imposter_id}'s hunt was interrupted")
        bot_memories[imposter_id].append(f"Interrupted while hunting {victim_id}")
        raise
    finally:
        if imposter_id in active_actions:
            del active_actions[imposter_id]
        
async def print_roles(parts, context):
    bots = context.get('bots')
    for bot, info in bots.items():
        print(f"{bot}: {info['role']}")
        
async def report_body(parts, context):
    active_connection = context.get('active_connection')
    
    bot_id = int(parts[0])
    
    payload = {
        "type": "command",
        "action": "report",
        "bot_id": bot_id
    }
    await active_connection.send(json.dumps(payload))
    interrupt_bot('all', context)
    
async def execute_sabotage(parts, context):
    interrupt_bot(parts[0], context)
    await sub.begin(parts, context)
    
async def fix_sabotage(parts, context):
    interrupt_bot(parts[0], context)
    await sub.fix(parts, context)
    
async def chat(parts, context):
    active_connection = context.get('active_connection')
    
    bot_id = int(parts[0])
    message = " ".join(parts[1:])
    
    payload = {
        "type": "command",
        "action": "chat",
        "bot_id": bot_id,
        "message": message
    }
    await active_connection.send(json.dumps(payload))
    print(f"Bot {bot_id} sent a message")
    
async def vote(parts, context):
    active_connection = context.get('active_connection')
    
    bot_id = int(parts[0])
    target_id = int(parts[1])
    
    payload = {
        "type": "command",
        "action": "vote",
        "bot_id": bot_id,
        "target_id": target_id
    }
    await active_connection.send(json.dumps(payload))
    print(f"Bot {bot_id} voted for bot {target_id}")
    
async def proceed(parts, context):
    active_connection = context.get('active_connection')
    
    payload = {
        "type": "command",
        "action": "proceed"
    }
    await active_connection.send(json.dumps(payload))

async def vent(parts, context):
    vent_commands = {
        "enter": sub.enter_vent,
        "move": sub.vent_move,
        "exit": sub.exit_vent
    }
    subcommand = vent_commands[parts[1]]
    await subcommand(parts, context)
    
async def wait_action(parts, context):
    bot_id = int(parts[0])
    duration = float(parts[1]) if len(parts) > 1 else 5.0
    
    active_actions = context.get('active_actions')
    narrator = context.get('narrator')
    generate_snapshot = context.get('generate_snapshot')
    
    print(f"Bot {bot_id} waiting for {duration} seconds")
    
    async def do_wait():
        try:
            await asyncio.sleep(duration)
            
            if narrator and generate_snapshot:
                state = generate_snapshot(bot_id)
                asyncio.create_task(
                    narrator.generate_action(
                        bot_id=bot_id,
                        state=state,
                        event_type="arrived",
                        event_kwargs={"current_room": state['current_room']}
                    )
                )
                
        except asyncio.CancelledError:
            print(f"Bot {bot_id}'s wait was interrupted.")
            context['bot_memories'][bot_id].append("Interrupted while waiting")
            raise
        
        finally:
            if bot_id in active_actions: del active_actions[bot_id]
            
    active_actions[bot_id] = asyncio.create_task(do_wait())