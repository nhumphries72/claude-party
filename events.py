import time
import asyncio
from cli_subfunctions import lock_doors
from cli_functions import interrupt_bot

def handle_events(event_context):
    data = event_context.get('data')
    bot_arrival_events = event_context.get('bot_arrival_events')
    active_actions = event_context.get('active_actions')
    cooldowns = event_context.get('cooldowns')
    nav = event_context.get('navigator')
    manager = event_context.get('manager')
    event = data.get("event_type")
    bot_id = data.get("bot_id")
    
    if event == "arrived":
        if bot_id in bot_arrival_events: bot_arrival_events[bot_id].set()
        
    elif event == "task_complete":
        print(f"\nBot {bot_id} completed {data.get('task_name')}")
        
    elif event == "kill_complete":
        target_id = data.get('target_id')
        print(f"Bot {target_id} was murdered by bot {bot_id}")
        if bot_id in active_actions: del active_actions[bot_id]
        cooldowns['kill'][bot_id] = time.time() + 45
        
    elif event == "sabotage_successful":
        system = data.get('system')
        room = data.get('room')
        print(f"Bot {bot_id} sabotaged {system}")
        cooldowns['sabotage'][bot_id] = time.time() + 30
        
        if system == "doors" and room != "none":
            asyncio.create_task(lock_doors(room, nav))
            
    elif event in ["emergency_meeting", "report"]:
        victim_id = data.get("victim_id") if event == "report" else None
        asyncio.create_task(manager.start_meeting(bot_id, victim_id))
        
    elif event == "corpse_spotted":
        corpse_id = data.get("corpse_id")
        #TODO: Talk to the narrator
        
    elif event == "witness":
        imposter_id = data.get("imposter_id")
        action = data.get("action")
        #TODO: Talk to the narrator
        