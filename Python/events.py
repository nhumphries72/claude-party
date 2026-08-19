import time
import asyncio
from sabotage_functions import lock_doors
from cli_functions import interrupt_bot

def handle_events(event_context):
    data = event_context.get('data')
    bot_arrival_events = event_context.get('bot_arrival_events')
    active_actions = event_context.get('active_actions')
    cooldowns = event_context.get('cooldowns')
    nav = event_context.get('navigator')
    
    if data.get("event_type") == "arrived":
        bot_id = data.get("bot_id")
        if bot_id in bot_arrival_events: bot_arrival_events[bot_id].set()
        
    elif data.get("event_type") == "task_complete":
        print(f"\nBot {data.get('bot_id')} completed {data.get('task_name')}")
        
    elif data.get("event_type") == "kill_complete":
        bot_id = data.get('bot_id')
        target_id = data.get('target_id')
        print(f"Bot {target_id} was murdered by bot {bot_id}")
        if bot_id in active_actions: del active_actions[bot_id]
        cooldowns['kill'][bot_id] = time.time() + 45
        
    elif data.get("event_type") == "sabotage_successful":
        bot_id = data.get('bot_id')
        system = data.get('system')
        room = data.get('room')
        print(f"Bot {bot_id} sabotaged {system}")
        cooldowns['sabotage'][bot_id] = time.time() + 30
        
        if system == "doors" and room != "none":
            asyncio.create_task(lock_doors(room, nav))