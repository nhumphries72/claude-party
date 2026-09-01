import asyncio
import json
import time

class MeetingManager:
    def __init__(self, active_connection, bots, active_actions, bot_arrival_events):
        self.connection = active_connection
        self.bots = bots
        self.active_actions = active_actions
        self.bot_arrival_events = bot_arrival_events
        
        self.game_phase = "roaming"
        self.context = {}
        
        self.response_queue = asyncio.Queue()
        
    async def start_meeting(self, caller_id, victim_id=None):
        if self.game_phase == "meeting": return
        
        self.game_phase = "meeting"
        
        for bot_id, task in self.active_actions.items():
            task.cancel()
        self.active_actions.clear()
        
        for event in self.bot_arrival_events.values():
            event.clear()
            
        living_bots = [bot_id for bot_id, info in self.bots.items() if info['alive']]
        self.context = {
            "caller_id": caller_id,
            "victim_id": victim_id,
            "chat_history": [],
            "votes_cast": {},
            "eligible_voters": living_bots
        }
        
        await self.run_lifecycle()
        
    async def run_lifecycle(self):
        
        await asyncio.sleep(2.5)
        
        meeting_duration = 135.0
        discussion_time = 15.0
        
        start_time = time.time()
        voting_opens_at = start_time + discussion_time
        meeting_ends_at = start_time + meeting_duration
        
        round_num = 1
        
        while time.time() < meeting_ends_at:
            voting_open = time.time() >= voting_opens_at
            print(f"\nMeeting round {round_num} | voting open: {voting_open}")
            
            #TODO: Implement narrator call here
            
            state_changed = await self._poll_round(voting_open, timeout=15.0)
            
            if len(self.context["votes_cast"]) == len(self.context["eligible_voters"]):
                print("All bots have voted. Concluding meeting.")
                break
            
            if not state_changed:
                print("Nobody wants to talk so they are being left in silence")
                time_left = meeting_ends_at - time.time()
                
                if not voting_open:
                    sleep_time = voting_opens_at - time.time()
                    if sleep_time > 0:
                        await asyncio.sleep(sleep_time)
                elif time_left > 15.0:
                    await asyncio.sleep(time_left - 15.0)
                else:
                    break
                
            round_num += 1
        
        print("\nMeeting concluded.")
        await self.connection.send(json.dumps({
            "type": "command",
            "action": "proceed"
        }))
            
    async def _poll_round(self, voting_open, timeout):
        expected_reponses = len(self.context["eligible_voters"])
        responses_received = 0
        state_changed = False
        
        start = time.time()
        while responses_received < expected_reponses:
            time_left = timeout - (time.time() - start)
            if time_left <= 0: break
            
            try:
                turn_data = await asyncio.wait_for(self.response_queue.get(), timeout=0.5)
                bot_id = turn_data.get("bot_id")
                responses_received += 1
                
                if turn_data.get("chat"):
                    message = turn_data["chat"]
                    self.context["chat_history"].append((bot_id, message))
                    state_changed = True
                
                    await self.connection.send(json.dumps({
                        "type": "command",
                        "action": "chat",
                        "bot_id": bot_id,
                        "message": message
                    }))
                    
                if turn_data.get("vote") and voting_open:
                    target = turn_data["vote"]
                    
                    if bot_id not in self.context["votes_cast"]:
                        self.context["votes_cast"][bot_id] = target
                        state_changed = True
                        
                        await self.connection.send(json.dumps({
                            "type": "command",
                            "action": "vote",
                            "bot_id": bot_id,
                            "target_id": target
                        }))
                        
            except asyncio.TimeoutError:
                continue
            
        return state_changed

                