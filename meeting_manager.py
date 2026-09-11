import asyncio
import json
import time
import websockets

class MeetingManager:
    def __init__(self, active_connection, bots, active_actions, bot_arrival_events):
        self.connection = active_connection
        self.bots = bots
        self.active_actions = active_actions
        self.bot_arrival_events = bot_arrival_events
        self.known_dead = set()
        
        self.game_phase = "roaming"
        self.voting_open = False
        self.context = {}
        
        self.response_queue = asyncio.Queue()
        
    async def start_meeting(self, caller_id, victim_id, narrator, snapshot_func):
        if self.game_phase == "meeting": return
        
        self.game_phase = "meeting"
        self.narrator = narrator
        self.generate_snapshot = snapshot_func
        
        for bot_id in self.bots:
            self.narrator.command_queue.put_nowait(f"stop {bot_id}")
        
        for bot_id, task in self.active_actions.items():
            task.cancel()
        self.active_actions.clear()
        
        for event in self.bot_arrival_events.values():
            event.clear()
            
        living_bots = [bot_id for bot_id, info in self.bots.items() if info['alive']]
        dead_bots = {bot_id for bot_id, info in self.bots.items() if not info['alive'] and info['role'] != "imposter"}
        new_dead = dead_bots - self.known_dead
        self.known_dead.update(new_dead)
        if new_dead:
            dead_str = ", ".join([f"Bot {b}" for b in new_dead])
            meeting_announcement = f"Players who have died since last meeting: {dead_str}"
        else:
            meeting_announcement = "No players have died since the previous meeting."
        
        self.context = {
            "caller_id": caller_id,
            "victim_id": victim_id,
            "chat_history": [],
            "votes_cast": {},
            "eligible_voters": living_bots,
            "meeting_announcement": meeting_announcement
        }
        
        await asyncio.sleep(4)
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
            self.voting_open = time.time() >= voting_opens_at
            print(f"\nMeeting round {round_num} | voting open: {self.voting_open}")
            
            while not self.response_queue.empty():
                try:
                    self.response_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            chat_log = "\n".join([f"Bot {b}: {msg}" for b, msg in self.context["chat_history"]])
            if not chat_log: chat_log = "No messages yet."
            
            reason = f"Reported Bot {self.context['victim_id']}'s body." if self.context.get('victim_id') else "Emergency button pressed."
            voting_status = "Open" if self.voting_open else "Closed"
            
            for bot_id in self.context["eligible_voters"]:
                state_snapshot = self.generate_snapshot(bot_id)
                has_voted = bot_id in self.context['votes_cast']
                state_snapshot['has_voted'] = has_voted
                if has_voted: voting_status = "You have already cast your vote."
                asyncio.create_task(
                    self.narrator.generate_action(
                        bot_id=bot_id,
                        state=state_snapshot,
                        event_type="meeting_turn",
                        event_kwargs={
                            "round_num": round_num,
                            "caller_id": self.context['caller_id'],
                            "reason": reason,
                            "chat_history": chat_log,
                            "voting_status": voting_status,
                            "meeting_announcement": self.context['meeting_announcement']
                        }
                    )
                )
            
            state_changed = await self._poll_round(timeout=15.0)
            
            if len(self.context["votes_cast"]) == len(self.context["eligible_voters"]):
                print("All bots have voted. Concluding meeting.")
                break
            
            if not state_changed:
                print("Nobody wants to talk so they are being left in silence")
                time_left = meeting_ends_at - time.time()
                
                if not self.voting_open:
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
        
        print("Waiting for ejection animation to complete")
        await asyncio.sleep(12.0)
        
        vote_counts = {}
        for voter, target in self.context['votes_cast'].items():
            vote_counts[target] = vote_counts.get(target, 0) + 1
            
        if not vote_counts:
            ejection_result = "No votes were counted. Nobody was ejected."
        else:
            max_votes = max(vote_counts.values())
            winners = [t for t, c in vote_counts.items() if c == max_votes]
            
            if len(winners) > 1:
                ejection_result = "The vote was tied. Nobody was ejected."
            elif winners[0] == 15:
                ejection_result = "The crew voted to skip. Nobody was ejected."
            else:
                ejected_id = winners[0]
                is_imposter = self.bots[ejected_id]['role'] == "imposter"
                role_Str = "an Imposter" if is_imposter else "not an Imposter"
                ejection_result = f"Bot {ejected_id} was ejected. They were {role_Str}"
                self.bots[ejected_id]['alive'] = False
        
        self.game_phase = "roaming"
        
        for bot_id in self.context['eligible_voters']:
            state = self.generate_snapshot(bot_id)
            asyncio.create_task(
                self.narrator.generate_action(
                    bot_id=bot_id,
                    state=state,
                    event_type="meeting_ended",
                    event_kwargs={"ejection_result": ejection_result}
                )
            )
            
            
    async def _poll_round(self, timeout):
        expected_reponses = len(self.context["eligible_voters"])
        responses_received = 0
        state_changed = False
        
        start = time.time()
        while responses_received < expected_reponses:
            time_left = timeout - (time.time() - start)
            if time_left <= 0: break
            
            try:
                turn_data = await asyncio.wait_for(self.response_queue.get(), timeout=0.5)
                bot_id = int(turn_data.get("bot_id"))
                responses_received += 1
                
                if turn_data.get("chat"):
                    message = turn_data["chat"]
                    self.context["chat_history"].append((bot_id, message))
                    state_changed = True

                    try:
                        await self.connection.send(json.dumps({
                            "type": "command",
                            "action": "chat",
                            "bot_id": bot_id,
                            "message": message
                        }))
                    except websockets.exceptions.ConnectionClosed:
                        print("Meeting interrupted: Unity disconnected")
                        return False
                    
                if turn_data.get("vote") and self.voting_open:
                    target = turn_data["vote"]
                    clean_target = 15 if target == "skip" else int(target)
                    
                    if bot_id not in self.context["votes_cast"]:
                        self.context["votes_cast"][bot_id] = clean_target
                        state_changed = True
                        
                        try:
                            await self.connection.send(json.dumps({
                                "type": "command",
                                "action": "vote",
                                "bot_id": bot_id,
                                "target_id": clean_target
                            }))
                        except websockets.exceptions.ConnectionClosed:
                            print("Meeting interrupted: Unity disconnected")
                            return False
                        
            except asyncio.TimeoutError:
                continue
            
        return state_changed

                