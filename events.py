import time
import asyncio
from cli_subfunctions import lock_doors

def _handle_arrived(bot_id, data, ctx):
    if bot_id in ctx['bot_arrival_events']: 
        ctx['bot_arrival_events'][bot_id].set()
    room = ctx['find_current_room'](bot_id)
    ctx['bot_memories'][bot_id].append(f"Arrived at {room}")

def _handle_kill_complete(bot_id, data, ctx):
    target_id = data.get('target_id')
    print(f"Bot {target_id} was murdered by bot {bot_id}")
    
    if bot_id in ctx['active_actions']: 
        del ctx['active_actions'][bot_id]
        
    ctx['cooldowns']['kill'][bot_id] = time.time() + 45
    ctx['bot_memories'][bot_id].append(f"Killed {target_id}")
    ctx['bot_memories'][target_id].append(f"Bot {bot_id} killed you")

def _handle_meeting_trigger(bot_id, data, ctx):
    event = data.get("event_type")
    victim_id = data.get("victim_id") if event == "report" else None
    
    asyncio.create_task(ctx['manager'].start_meeting(bot_id, victim_id))
    
    if event == "emergency_meeting":
        ctx['bot_memories'][bot_id].append("Called an emergency meeting")
    else:
        ctx['bot_memories'][bot_id].append(f"Reported bot {victim_id}'s body")

def _handle_sabotage(bot_id, data, ctx):
    system, room = data.get('system'), data.get('room')
    print(f"Bot {bot_id} sabotaged {system}")
    ctx['cooldowns']['sabotage'][bot_id] = time.time() + 30
    
    if system == "doors" and room != "none":
        asyncio.create_task(lock_doors(room, ctx['navigator']))
        
    ctx['bot_memories'][bot_id].append(f"Sabotaged the {system} system")
    
def _handle_task(bot_id, data, ctx):
    print(f"Bot {bot_id} completed {data.get('task_name')}")
    ctx['bot_memories'][bot_id].append(f"Finished task {data.get('task_name')}")
    
def _handle_corpse_spotted(bot_id, data, ctx):
    ctx['bot_memories'][bot_id].append(f"Spotted bot {data.get('corpse_id')}'s body")
    
def _handle_witness(bot_id, data, ctx):
    ctx['bot_memories'][bot_id].append(f"Witnessed bot {data.get('imposter_id')} {data.get('action')}")
    
def _handle_vent(bot_id, data, ctx):
    ctx['bot_memories'][bot_id].append(f"Traveled to {ctx['find_current_room'](bot_id)} through a vent")
    
def handle_events(event_context):
    data = event_context.get('data')
    event = data.get('event_type')
    bot_id = int(data.get('bot_id'))
    
    handler = EVENT_HANDLERS.get(event)
    
    if handler:
        handler(bot_id, data, event_context)
    else:
        print(f"Unknown event: {event}")
        
EVENT_HANDLERS = {
    "kill_complete": _handle_kill_complete,
    "emergency_meeting": _handle_meeting_trigger,
    "report": _handle_meeting_trigger,
    "sabotage_successful": _handle_sabotage,
    "task_complete": _handle_task,
    "corpse_spotted": _handle_corpse_spotted,
    "witness": _handle_witness,
    "exit_vent": _handle_vent
}
        
    