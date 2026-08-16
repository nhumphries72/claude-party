using HarmonyLib;

namespace Amogus
{
    [HarmonyPatch(typeof(PlayerControl), nameof(PlayerControl.Die))]
    public static class DeathPatch
    {
        public static void Prefix(PlayerControl __instance)
        {
            if (__instance != null && PlayerControl.LocalPlayer != null)
            {
                if (__instance.PlayerId != PlayerControl.LocalPlayer.PlayerId)
                {
                    Plugin.Instance.Log.LogInfo($"Bot {__instance.PlayerId} is dying, temporarily revoking ownership...");
                    __instance.OwnerId = 999;
                }
            }
        }

        public static void Postfix(PlayerControl __instance)
        {
            if (__instance != null && PlayerControl.LocalPlayer != null)
            {
                if (__instance.PlayerId != PlayerControl.LocalPlayer.PlayerId)
                {
                    if (AmongUsClient.Instance != null)
                    {
                        __instance.OwnerId = AmongUsClient.Instance.ClientId;
                        Plugin.Instance.Log.LogInfo($"Restored ownership for bot {__instance.PlayerId}");
                    }
                }
            }
        }
    }
}