using System;
using HarmonyLib;

namespace Amogus
{
    [HarmonyPatch(typeof(KillOverlay), nameof(KillOverlay.ShowKillAnimation), [typeof(NetworkedPlayerInfo), typeof(NetworkedPlayerInfo)])]
    public static class KillScreenPatch
    {
        public static bool Prefix(KillOverlay __instance, NetworkedPlayerInfo killer, NetworkedPlayerInfo victim)
        {
            if (killer?.PlayerId != PlayerControl.LocalPlayer?.PlayerId &&
            victim?.PlayerId != PlayerControl.LocalPlayer?.PlayerId)
            {
                return false;
            }
            else
            {
                return true;
            }
        }
    }
}