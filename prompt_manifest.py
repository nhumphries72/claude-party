IDENTITY = {
    "crewmate": """<system>
    You are playing a simulated game of Among Us.
    You are Bot {bot_id}. You are {color}. You are a Crewmate.
    Your goal is to complete all of your tasks or vote out all Imposters.
    </system>""",
    
    "imposter": """<system>
    You are playing a simulated game of Among Us.
    You are Bot {bot_id}. You are {color}. You are an Imposter.
    Your goal is to kill all Crewmates without being caught.
    </system>
    """
}

STATE = """<context>
Location: {current_room}
Status: {status}
Visible players in room: {visible_players}
Visible corpses: {visible_corpses}
Active Emergency: {active_sabotage}
{imposter_str}

Your tasks (if you are an Imposter, these are fake tasks):
{task_list}

Emergency Meetings Remaining: {meetings_remaining}
{cooldown_text}

Recent memory:
{memory_log}

Match notes:
{match_notes}
</context>
"""

EVENTS = {
    "match_start": """<event>
    The game has just begun. All players begin in the Cafeteria. What is your first move?
    </event>""",
    
    "arrived": """<event>
    You have arrived at {current_room}. What is your next move?
    </event>""",
    
    "task_progress": """<event>
    You completed a stage of your task: {task_name}. What is your next move?
    </event>""",
    
    "task_complete": """<event>
    You fully completed your task: {task_name}. What is your next move?
    </event>""",
    
    "task_faked": """<event>
    You pretended to complete the task: {task_name}. What is your next move?
    </event>""",
    
    "kill_complete": """<event>
    You killed Bot {target_id}. You are now standing above a corpse. What is your next move?
    </event>""",
    
    "sabotage_successful": """<event>
    You triggered a sabotage. You can help fix the sabotage you started, or use the opportunity to do something else. What is your next move?
    </event>""",

    "corpse_spotted": """<event>
    You spotted a corpse. What is your next move?
    </event>""",
    
    "witness": """<event>
    You witnessed Bot {imposter_id} {action}. What is your next move?
    </event>""",
    
    "enter_vent": """<event>
    You entered a vent into {current_room}. What is your next move?
    </event>""",
    
    "vent_move": """<event>
    You are now in the vent in {current_room}. What is your next move?
    </event>""",
    
    "exit_vent": """<event>
    You exited the vent into {current_room}. What is your next move?
    </event>""",
    
    "fix_successful": """<event>
    You repaired a sabotage. What is your next move?
    </event>""",
    
    "interrupted": """<event>
    You were interrupted by {interruption_reason}. What is your next move?
    </event>""",
    
    "meeting_turn": """<event>
    Emergency meeting. Round {round_num}.
    Caller: Bot {caller_id}
    Reason: {reason}
    
    Chat History: {chat_history}
    
    Voting is currently: {voting_status}
    What do you say or do?
    </event>""",
    
    "death": """<event>
    You are dead. You are now a ghost. You cannot be seen by living players, participate in meetings, murder other players, or fix sabotages. However, you can still complete tasks if you are a crewmate, and begin sabotages if you are an imposter.
    Dead crewmates must still complete their tasks to win.
    </event>""",
    
    "error": """<event>
    ERROR: {error_message}. Please rethink and output a valid <action> command.
    </event>"""
}

COMMAND_DOCS = {
    "wait": """<action>wait [seconds]</action>
Stand still for the specified duration.""",
    
    "move": """<action>move [room]</action>
[room] must be one of: {valid_rooms}""",
    
    "task": """<action>task [task_number]</action>
Work on a task from your list. You will automatically route there if needed.""",
    
    "meeting": """<action>meeting</action>
Call an emergency meeting. You will automatically route to the Cafeteria. You can only do this one time.""",
    
    "fix": """<action>fix [system]</action>
Automatically route to and repair the system being sabotaged.""",

    "report": """<action>report</action>
Report the corpse you just saw (or created).""",

    "kill": """<action>kill [target_bot_id]</action>
Hunt down and murder a Crewmate. Hunting crewmates that are not currently in sight may result in unexpected witnesses.""",

    "sabotage": """<action>sabotage [system]</action>
[system] must be one of: Lights, Comms, or Doors.
If sabotaging doors, append the room (e.g., <action>sabotage doors Storage</action>).""",

    "vent_enter": """<action>vent enter [room]</action>
Enter a vent in your current room. If in Navigation or Reactor, specify north/south (e.g., <action>vent enter Navigation north</action>).""",

    "vent_move": """<action>vent move [room]</action>
Move to a connected vent. Connected vents: {connected_vents}""",

    "vent_exit": """<action>vent exit</action>
Exit the vent system into your current room.""",

    "chat": """<action>chat [message]</action>
Broadcast a message to all players.""",

    "vote": """<action>vote [bot_id or "skip"]</action>
Vote to eject a player, or vote "skip" if you aren't suspicious of anyone."""
}