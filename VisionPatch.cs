using System.Collections.Generic;
using UnityEngine;

namespace Amogus
{
    public class VisionContainer
    {
        public List<PlayerControl> VisiblePlayers = [];
        public List<DeadBody> VisibleCorpses = [];
    }

    public static class BotVision
    {
        public static void WitnessCrime(PlayerControl imposter, string actionType, int targetId = 15)
        {
            foreach (var witness in PlayerControl.AllPlayerControls)
            {
                if (witness.PlayerId == imposter.PlayerId || witness.Data.IsDead) continue;

                VisionContainer vision = GetVisibleEntitites(witness);

                if (vision.VisiblePlayers.Contains(imposter))
                {
                    string target = targetId != 15 ? $", \"target_id\": {targetId}": "";
                    string payload = $"{{\"type\": \"event\", \"event_type\": \"witness\", \"witness_id\": {witness.PlayerId}, \"imposter_id\": {imposter.PlayerId}, \"action\": {actionType}{target}}}";
                    WebSocketManager.Send(payload);
                }
            }
        }
        public static VisionContainer GetVisibleEntitites(PlayerControl bot, DeadBody[] allCorpses = null)
        {
            VisionContainer report = new();

            if (bot == null || bot.Data == null)
            {
                return report;
            }

            float sightRadius = 5.0f;
            
            if (bot.Data.Role.IsImpostor)
            {
                sightRadius *= 1.5f;
            }
            else if (ShipStatus.Instance?.Systems != null)
            {
                if (ShipStatus.Instance.Systems.TryGetValue(SystemTypes.Electrical, out ISystemType electricalSystem))
                {
                    var switchSystem = electricalSystem.Cast<SwitchSystem>();
                    if (switchSystem != null)
                    {
                        float lightLevel = switchSystem.Value / 255f;
                        if (lightLevel < 1.0f) { sightRadius = Mathf.Lerp(1.0f, sightRadius, lightLevel); }
                    }
                }
            }

            int wallMask = Constants.ShadowMask;
            Vector2 botPos = bot.transform.position;

            foreach (var otherPlayer in PlayerControl.AllPlayerControls)
            {
                if (otherPlayer.PlayerId == bot.PlayerId || otherPlayer.Data.IsDead)
                {
                    continue;
                }

                float dist = Vector2.Distance(botPos, otherPlayer.transform.position);
                if (dist <= sightRadius)
                {
                    RaycastHit2D hit = Physics2D.Linecast(botPos, otherPlayer.transform.position, wallMask);
                    if (hit.collider == null)
                    {
                        report.VisiblePlayers.Add(otherPlayer);
                    }
                }
            }

            if (allCorpses != null)
            {
                foreach (var body in allCorpses)
                {
                    float dist = Vector2.Distance(botPos, body.transform.position);
                    if (dist <= sightRadius)
                    {
                        RaycastHit2D hit = Physics2D.Linecast(botPos, body.transform.position, wallMask);
                        if (hit.collider == null)
                        {
                            report.VisibleCorpses.Add(body);
                        }
                    }
                }
            }
            return report;
        }
    }
}