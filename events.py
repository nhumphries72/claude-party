import time
import asyncio
from cli_subfunctions import lock_doors

def _handle_arrived(bot_id, data, ctx):
    if bot_id in ctx['bot_arrival_events']: 
        ctx['bot_arrival_events'][bot_id].set()
    room = ctx['find_current_room'](bot_id)
    
    last_memory = ctx['bot_memories'][bot_id][-1] if ctx['bot_memories'][bot_id] else""
    if last_memory != f"Arrived at {room}": ctx['bot_memories'][bot_id].append(f"Arrived at {room}")
    
    return None

def _handle_kill_complete(bot_id, data, ctx):
    target_id = int(data.get('target_id'))
    print(f"Bot {target_id} was murdered by bot {bot_id}")
    
    if bot_id in ctx['active_actions']: 
        del ctx['active_actions'][bot_id]
    
    if target_id in ctx['active_actions']:
        ctx['active_actions'][target_id].cancel()
        del ctx['active_actions'][target_id]
        
    ctx['cooldowns']['kill'][bot_id] = time.time() + 45
    ctx['bot_memories'][bot_id].append(f"Killed {target_id}")
    ctx['bot_memories'][target_id].append(f"Bot {bot_id} killed you")
    ctx['bots'][target_id]['alive'] = False
    
    target_state = ctx['generate_snapshot'](target_id)
    asyncio.create_task(
        ctx['narrator'].generate_action(
            bot_id=target_id,
            state=target_state,
            event_type="death",
            event_kwargs={}
        )
    )
    
    return {"target_id": target_id}

def _handle_meeting_trigger(bot_id, data, ctx):
    event = data.get("event_type")
    victim_id = data.get("victim_id") if event == "report" else None
    
    asyncio.create_task(
        ctx['manager'].start_meeting(
            caller_id=bot_id,
            victim_id=victim_id,
            narrator=ctx['narrator'],
            snapshot_func=ctx['generate_snapshot']
        )
    )
    
    if event == "emergency_meeting":
        ctx['bot_memories'][bot_id].append("Called an emergency meeting")
        ctx['meetings_remaining'][bot_id] -= 1
    else:
        ctx['bot_memories'][bot_id].append(f"Reported bot {victim_id}'s body")
        
    return None

def _handle_sabotage(bot_id, data, ctx):
    system, room = data.get('system'), data.get('room')
    print(f"Bot {bot_id} sabotaged {system}")
    ctx['cooldowns']['sabotage'][bot_id] = time.time() + 30
    
    if system == "doors" and room != "none":
        asyncio.create_task(lock_doors(room, ctx['navigator']))
        
    ctx['bot_memories'][bot_id].append(f"Sabotaged the {system} system")
    ctx['active_sabotage']['system'] = system
    return {}
    
def _handle_task(bot_id, data, ctx):
    print(f"Bot {bot_id} completed {data.get('task_name')}")
    ctx['bot_memories'][bot_id].append(f"Finished task {data.get('task_name')}")
    return None
    
def _handle_corpse_spotted(bot_id, data, ctx):
    if ctx['is_dead'](bot_id): return None
    
    if bot_id in ctx['active_actions']:
        ctx['active_actions'][bot_id].cancel()
        del ctx['active_actions'][bot_id]
    
    corpse_id = data.get('corpse_id')
    
    if 'visible_corpses' not in ctx['bots'][bot_id]:
        ctx['bots'][bot_id]['visible_corpses'] = []
        
    if corpse_id not in ctx['bots'][bot_id]['visible_corpses']:
        ctx['bots'][bot_id]['visible_corpses'].append(corpse_id)
    
    last_memory = ctx['bot_memories'][bot_id][-1] if ctx['bot_memories'][bot_id] else ""
    if f"Killed {corpse_id}" in last_memory: return None
    
    ctx['bot_memories'][bot_id].append(f"Spotted bot {corpse_id}'s body")
    return {}
    
def _handle_witness(bot_id, data, ctx):
    imposter_id, action = data.get('imposter_id'), data.get('action')
    if ctx['is_dead'](bot_id): return None
    
    if bot_id in ctx['active_actions']:
        ctx['active_actions'][bot_id].cancel()
        del ctx['active_actions'][bot_id]
    
    ctx['bot_memories'][bot_id].append(f"Witnessed bot {imposter_id} {action}")
    return {
        "imposter_id": imposter_id,
        "action": action
    }
    
def _handle_vent(bot_id, data, ctx):
    ctx['bot_memories'][bot_id].append(f"Traveled to {ctx['find_current_room'](bot_id)} through a vent")
    return {}
    
def _handle_fix(bot_id, data, ctx):
    ctx['bot_memories'][bot_id].append(f"Fixed a {data.get('system')} sabotage")
    ctx['active_sabotage']['system'] = None
    if (data.get('system'), data.get('panel')) in ctx['sabotage_being_fixed']:
        ctx['sabotage_being_fixed'].remove((data.get('system'), data.get('panel')))
    return {}

def _handle_message(bot_id, data, ctx):
    return None

def _handle_end_meeting(bot_id, data, ctx):
    print("Meeting concluded successfully")
    return None

def _handle_report(bot_id, data, ctx):
    victim = data.get('victim_id')
    print(f"Bot {bot_id} reported bot {victim}'s body")
    
    asyncio.create_task(ctx['manager'].start_meeting(caller_id=bot_id, victim_id=victim, narrator=ctx['narrator'], snapshot_func=ctx['generate_snapshot']))
    
    return None

def _handle_vote(bot_id, data, ctx):
    return None
    
def handle_events(event_context):
    data = event_context.get('data')
    event = data.get('event_type')
    bot_id = int(data.get('bot_id', 15))
    narrator = event_context.get('narrator')
    
    handler = EVENT_HANDLERS.get(event)
    
    if handler:
        event_kwargs = handler(bot_id, data, event_context)
        if event_kwargs is not None:
            state = event_context.get('generate_snapshot')(bot_id) 
            asyncio.create_task(
            narrator.generate_action(
                bot_id=bot_id,
                state=state,
                event_type=event,
                event_kwargs=event_kwargs
                )
            )
    else:
        print(f"Unknown event: {event}")
        
EVENT_HANDLERS = {
    "arrived": _handle_arrived,
    "kill_complete": _handle_kill_complete,
    "emergency_meeting": _handle_meeting_trigger,
    "report": _handle_meeting_trigger,
    "sabotage_successful": _handle_sabotage,
    "task_complete": _handle_task,
    "corpse_spotted": _handle_corpse_spotted,
    "witness": _handle_witness,
    "exit_vent": _handle_vent,
    "fix_successful": _handle_fix,
    "message": _handle_message,
    "end_meeting": _handle_end_meeting,
    "report": _handle_report,
    "vote": _handle_vote
}
        
    