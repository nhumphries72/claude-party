import asyncio
import re
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage
import prompt_manifest as manifest
from datetime import datetime

ROOM_ALIASES = {
    "cafeteria": "Cafeteria", "cafe": "Cafeteria",
    "lifesupp": "LifeSupp", "o2": "LifeSupp", "oxygen": "LifeSupp",
    "medbay": "MedBay", "med bay": "MedBay", "clinic": "MedBay",
    "admin": "Admin", "administration": "Admin",
    "electrical": "Electrical", "elec": "Electrical",
    "storage": "Storage",
    "weapons": "Weapons", "weaps": "Weapons",
    "navigation": "Navigation", "nav": "Navigation",
    "communications": "Comms", "comms": "Comms",
    "shields": "Shields",
    "reactor": "Reactor",
    "upper engine": "UpperEngine", "upperengine": "UpperEngine",
    "lower engine": "LowerEngine", "lowerengine": "LowerEngine",
    "security": "Security", "cameras": "Security", "cams": "Security"
}        

SYSTEM_ALIASES = {
    "reactor": "reactor", "meltdown": "reactor",
    "lifesupp": "lifesupp", "o2": "lifesupp", "oxygen": "lifesupp",
    "lights": "lights", "electrical": "lights",
    "comms": "comms", "communications": "comms"
}

class Narrator:
    def __init__(self, command_queue, meeting_manager):
        self.command_queue = command_queue
        self.manager = meeting_manager
        
        self.options = ClaudeAgentOptions(
            system_prompt="You are an AI playing Among Us. Follow XML rules strictly.",
            permission_mode="dontAsk"
        )
        self.max_retries = 2
        
    async def generate_action(self, bot_id, state, event_type, event_kwargs=None):
        if event_kwargs is None: event_kwargs = {}
        
        error_message = None
        
        for attempt in range(self.max_retries + 1):
            full_prompt = self._compile_prompt(bot_id, state, event_type, event_kwargs)
            
            response_text = await self._query_llm(full_prompt)
            if not response_text:
                error_message = "API returned empty response"
                continue
            
            actions = self._parse_xml(response_text)
            if not actions:
                error_message = "No <action> tag found. You must format your decision inside <action> tags."
                continue
            
            valid_actions, validation_error = self._validate_actions(actions, state)
            
            if validation_error:
                error_message = validation_error
                continue
            
            self._log_interaction(bot_id, state, event_type, full_prompt, response_text, valid_actions)
            self._route_actions(bot_id, valid_actions, state)
            return
        
        print(f"Bot {bot_id} hit retry cap. Forcing failsafe.")
        self._execute_failsafe(bot_id, state)
        
    async def _query_llm(self, prompt_string):
        response_text = ""
        
        try:
            async for message in query(prompt=prompt_string, options=self.options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, 'text'):
                            response_text += block.text
            return response_text
        except Exception as e:
            print(f"API Error: {e}")
            return None
        
    def _execute_failsafe(self, bot_id, state):
        if self.manager.game_phase == "meeting":
            self.manager.response_queue.put_nowait({"bot_id": bot_id, "wait": True})
        else:
            self.command_queue.put_nowait(f"wait {bot_id} 5")
            
    def _log_interaction(self, bot_id, state, event_type, prompt, response, actions):
        color = state.get('color')
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        log_entry = f"=== {timestamp} | Bot {bot_id} ({color}) | Event: {event_type} ===\n"
        log_entry += f"--- Prompt ---\n{prompt}\n\n"
        log_entry += f"--- Response ---\n{response}\n\n"
        log_entry += f"--- Parsed Actions ---\n{actions}\n\n\n"
        
        with open("monologues.txt", "a", encoding="utf-8") as f:
            f.write(log_entry)
            
    def _parse_xml(self, response_text):
        return re.findall(
            r'<action>\s*(.*?)\s*</action>',
            response_text, re.IGNORECASE | re.DOTALL
        )
        
    def _normalize_argument(self, action_string):
        parts = action_string.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        arg_lower = arg.lower().strip().replace('[', '').replace(']', '')
        
        if cmd == "move":
            arg = ROOM_ALIASES.get(arg_lower, arg)
        elif cmd == "vent":
            vent_parts = arg_lower.split(maxsplit=1)
            if len(vent_parts) == 2:
                sub_cmd, room_arg = vent_parts[0], vent_parts[1]
                
                dir_suffix = ""
                if room_arg.endswith(" north"):
                    room_arg, dir_suffix = room_arg[:-6].strip(), " north"
                elif room_arg.endswith(" south"):
                    room_arg, dir_suffix = room_arg[:-6].strip(), " south"
                
                fixed_room = ROOM_ALIASES.get(room_arg, vent_parts[1])
                arg = f"{sub_cmd} {fixed_room}{dir_suffix}"
        elif cmd == "sabotage":
            if arg_lower.startswith("doors "):
                room_part = arg_lower.replace("doors ", "").strip()
                fixed_room = ROOM_ALIASES.get(room_part, room_part)
                arg = f"doors {fixed_room}"
            else:
                arg = SYSTEM_ALIASES.get(arg_lower, arg)
                
        return cmd, arg
    
    def _validate_actions(self, actions, state):
        normalized_actions = []
        allowed_cmds = self._get_allowed_command_keys(state)
        
        for raw_action in actions:
            cmd, arg = self._normalize_argument(raw_action)
            
            if cmd not in allowed_cmds:
                return None, f"Command '{cmd}' is either invalid or unavailable right now."
            if cmd in ["move", "sabotage"] and not arg:
                return None, f"The '{cmd}' command requires an argument."
            
            normalized_actions.append((cmd, arg))
            
        if self.manager.game_phase == "roaming" and len(normalized_actions) > 1:
            normalized_actions = [normalized_actions[0]]
            
        return normalized_actions, None
    
    def _route_actions(self, bot_id, valid_actions, state):
        
        if self.manager.game_phase == "meeting":
            turn_data = {"bot_id": bot_id}
            for cmd, arg in valid_actions:
                if cmd == "chat":
                    turn_data["chat"] = arg
                elif cmd == "vote":
                    turn_data["vote"] = arg
                elif cmd == "wait":
                    turn_data["wait"] = True
            
            self.manager.response_queue.put_nowait(turn_data)
        
        else:
            for cmd, arg in valid_actions:
                cli_command = f"{cmd} {bot_id} {arg}".strip()
                self.command_queue.put_nowait(cli_command)
                
    def _get_allowed_command_keys(self, state):
        keys = ["wait"]
        
        if self.manager.game_phase == "meeting":
            if not state.get('alive'): return keys
            keys.append("chat")
            if self.manager.voting_open and not state.get("has_voted"):
                keys.append("vote")
            return keys
        
        if not state.get('alive'):
            keys.append('move')
            if len(state.get('tasks', [])) > 0:
                keys.append('task')
            if state.get('role') == "imposter":
                keys.append('sabotage')
            return keys
        
        if len(state.get('tasks', [])) > 0: keys.append('task')
        if not state.get("in_vent"): keys.append("move")
        if state.get("meetings_remaining") > 0: keys.append("meeting")
        if state.get("active_sabotage") in ["lights", "o2", "comms", "reactor"]: keys.append("fix")
        if state.get("role") == "imposter": keys.extend(["kill", "sabotage", "vent"])
        if len(state.get('visible_corpses', [])) > 0: keys.append("report")
        
        return keys
    
    def _get_available_command_docs(self, state):
        
        allowed_keys = self._get_allowed_command_keys(state)
        formatted_docs = []
        
        doc_kwargs = {
            "valid_rooms": ", ".join(sorted(set(ROOM_ALIASES.values()))),
            "active_sabotage": state.get("active_sabotage", "None")
        }
        
        for key in allowed_keys:
            raw_doc = manifest.COMMAND_DOCS.get(key)
            if raw_doc:
                formatted_docs.append(raw_doc.format(**doc_kwargs))
                
        return formatted_docs
    
    def _compile_prompt(self, bot_id, state, event_type, event_kwargs, error_message=None):
        
        role = state.get('role')
        identity = manifest.IDENTITY.get(role).format(bot_id=bot_id, color=state.get('color'))
        
        task_strings = []
        for i, t in enumerate(state.get('tasks', [])):
            base_str = f"{i+1}. {t['task']} (Location: {t['room']})"
            if t.get('cooldown_remaining'): base_str += f". {t['cooldown_remaining']} seconds until this task can be completed."
            task_strings.append(base_str)
        task_list_str = "\n".join(task_strings)
        
        imposter_str = ""
        if state.get('role') == "imposter":
            teammates = state.get('other_imposters')
            imposter_str = f"Other imposters: {teammates}\n"    
        
        memory_str = "\n".join(state.get('memory_log', []))
        current_status = "Alive" if state.get("alive") else "Dead"
        
        k_cd = state.get('kill_cooldown')
        s_cd = state.get('sabotage_cooldown')
        cooldown_text = ""
        if state.get('role') == "imposter":
            k_str = f"{int(k_cd)}s" if k_cd else "Ready"
            s_str = f"{int(s_cd)}s" if s_cd else "Ready"
            cooldown_text = f"Kill Cooldown: {k_str} | Sabotage Cooldown: {s_str}"
        
        state_block = manifest.STATE.format(
            current_room = state.get("current_room"),
            status = current_status,
            visible_players = ", ".join([str(p) for p in state.get("visible_players", [])]),
            visible_corpses = ", ".join([str(c) for c in state.get("visible_corpses", [])]),
            active_sabotage = state.get('active_sabotage') or 'None',
            imposter_str = imposter_str,
            task_list = task_list_str if task_list_str else "All tasks complete.",
            meetings_remaining = state.get('meetings_remaining'),
            cooldown_text = cooldown_text,
            memory_log = memory_str if memory_str else "No recent memories.",
            match_notes = state.get("match_notes", "None.")
        )
        
        if error_message:
            event_str = manifest.EVENTS["error"].format(error_message=error_message)
        else:
            raw_event = manifest.EVENTS.get(event_type, "<event>What is your next move?</event>")
            try:
                event_str = raw_event.format(**event_kwargs)
            except KeyError as e:
                print(f"Missing kwarg for event {event_type}: {e}")
                event_str = raw_event
        
        command_docs = self._get_available_command_docs(state)
        rules_block = "<rules>\nYou must output exactly one action using the strict XML formats below:\n\n"
        rules_block += "\n".join(command_docs)
        rules_block += "\n</rules>"
        
        return f"{identity}\n\n{state_block}\n\n{event_str}\n\n{rules_block}"
        
        
        