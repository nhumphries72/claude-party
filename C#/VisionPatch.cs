using System.Collections.Generic;
using UnityEngine;
using HarmonyLib;

namespace Amogus
{
    public class VisionContainer
    {
        public List<PlayerControl> VisiblePlayers = [];
        public List<DeadBody> VisibleCorpses = [];
    }

    public static class BotVision
    {
        public static VisionContainer GetVisibleEntitites(PlayerControl bot)
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

            DeadBody[] corpses = Object.FindObjectsOfType<DeadBody>();
            foreach (var body in corpses)
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
            return report;
        }
    }
}