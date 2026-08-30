import asyncio
import time
import os
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

async def query_sdk(bot_id, prompt):
    start_time = time.time()
    response_text = ""
    
    try:
        opts = ClaudeAgentOptions(permission_mode="dontAsk")
        async for message in query(prompt=prompt, options=opts):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
        
        duration = time.time() - start_time
        return {
            "bot_id": bot_id,
            "response": response_text.strip(),
            "error": None,
            "time_taken": round(duration, 2),
            "status": "Success"
        }
        
    except Exception as e:
        return {
            "bot_id": bot_id,
            "error": str(e),
            "time_taken": round(time.time() - start_time, 2),
            "status": "Failed"
        }
        
async def run_stress_test():
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("Error: environment variable not set")
        return
    
    print("Begin test")
    
    base_prompt = "You are Bot X in a simulation. Output exactly one sentence acknowledging this."
    
    tasks = []
    for i in range(1, 16):
        prompt = base_prompt.replace("X", str(i))
        tasks.append(query_sdk(i, prompt))
        
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    total_duration = time.time() - start_time
    
    print(f"\n--- TEST RESOLVED IN {round(total_duration, 2)} SECONDS ---")
    
    success_count = 0
    for r in results:
        if r['status'] == "Success":
            resp_snippet = r['response'][:60].replace('\n', ' ') + "..."
            print(f"[BOT {r['bot_id']}] {r['time_taken']}s | SUCCESS | {resp_snippet}")
            success_count += 1
        else:
            err_snippet = str(r['error'])[:100].replace('\n', ' ')
            print(f"[BOT {r['bot_id']}] {r['time_taken']}s | FAILED  | {err_snippet}")
            
    print(f"\nFinal Score: {success_count}/15 processes succeeded.")
    
    if success_count < 15:
        return False
    else:
        return True
    
if __name__ == "__main__":
    results = []
    for i in range(100):
        results.append(asyncio.run(run_stress_test()))
    print(f"Successes: {results.count(True)}, Failures: {results.count(False)}")
    