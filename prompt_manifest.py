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
Visible players in room: {visible_players}
Visible corpses: {visible_corpses}

Your tasks (if you are an Imposter, these are fake tasks):
{task_list}

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
    You completed a stage of your task. What is your next move?
    </event>""",
    
    "task_complete": """<event>
    You fully completed your task. What is your next move?
    </event>""",
    
    "interrupted": """<event>
    You were interrupted by {interruption_reason}. What is your next move?
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
    
    "fix": """<action>fix</action>
Automatically route to and repair the active sabotage ({active_sabotage}).""",

    "report": """<action>report</action>
Report the corpse you just saw (or created).""",

    "kill": """<action>kill [target_bot_id]</action>
Hunt down and murder a Crewmate. Hunting crewmates that are not currently in sight may result in unexpected witnesses.""",

    "sabotage": """<action>sabotage [system]</action>
[system] must be one of: Reactor, LifeSupp, Lights, Comms, or Doors.
If sabotaging doors, append the room (e.g., <action>sabotage doors Storage</action>).""",

    "vent_enter": """<action>vent enter [room]</action>
Enter a vent in your current room. If in Navigation or Reactor, specify north/south (e.g., <action>vent enter Navigation north</action>).""",

    "vent_move": """<action>vent move [room]</action>
Move to a connected vent.""",

    "vent_exit": """<action>vent exit</action>
Exit the vent system into your current room."""
}