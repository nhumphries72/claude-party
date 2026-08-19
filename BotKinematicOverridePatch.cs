using HarmonyLib;
using UnityEngine;

namespace Amogus
{
    
    [HarmonyPatch(typeof(PlayerPhysics), nameof(PlayerPhysics.FixedUpdate))]
    public static class BotKinematicOverridePatch
    {
        public static void Postfix(PlayerPhysics __instance)
        {
            
            if (__instance.myPlayer == null) return;

            byte botId = __instance.myPlayer.PlayerId;

            if (Plugin.PendingStops.TryRemove(botId, out _))
            {
                Plugin.ActiveNavigations.TryRemove(botId, out _);
                Plugin.ActiveHunts.TryRemove(botId, out _);
                var rb = __instance.GetComponent<Rigidbody2D>();
                rb?.velocity = Vector2.zero;
                return;
            }

            
            if (Plugin.ActiveHunts.TryGetValue(botId, out byte targetId))
            {
                var rb = __instance.GetComponent<Rigidbody2D>();
                if (rb == null) return;

                PlayerControl imposter = Plugin.IDToBot(botId);
                PlayerControl victim = Plugin.IDToBot(targetId);

                if (victim == null || victim.Data.IsDead)
                {
                    Plugin.ActiveHunts.TryRemove(botId, out _);
                    return;
                }

                float distance = Vector2.Distance(__instance.transform.position, victim.transform.position);
                float killRadius = 1.8f;

                if (distance <= killRadius)
                {
                    imposter.RpcMurderPlayer(victim, true);
                    Plugin.ActiveHunts.TryRemove(botId, out _);
                    rb.velocity = Vector2.zero;

                    string payload = $"{{\"type\": \"event\", \"event_type\": \"kill_complete\", \"bot_id\": {botId}, \"target_id\": {targetId}}}";
                    WebSocketManager.Send(payload);
                }
                else
                {
                    Vector2 direction = ((Vector2)victim.transform.position - (Vector2)__instance.transform.position).normalized;
                    float speed = __instance.TrueSpeed;

                    rb.velocity = direction * speed;
                }
            }

            else if (Plugin.ActiveNavigations.TryGetValue(botId, out Vector2 target))
            {
                var rb = __instance.GetComponent<Rigidbody2D>();
                if (rb == null) return;

                float distance = Vector2.Distance(__instance.transform.position, target);

                if (distance <= 0.1f)
                {
                    rb.velocity = Vector2.zero;
                    __instance.transform.position = target;
                    Plugin.ActiveNavigations.TryRemove(botId, out _);

                    string payload = $"{{\"type\": \"event\", \"event_type\": \"arrived\", \"bot_id\": {botId}}}";
                    WebSocketManager.Send(payload);

                    Plugin.Instance.Log.LogInfo($"Bot {botId} arrived at target.");
                }
                else
                {
                    Vector2 direction = (target - (Vector2)__instance.transform.position).normalized;
                    float speed = __instance.TrueSpeed;

                    rb.velocity = direction * speed;

                }
            }

        }
    }
}