using HarmonyLib;
using System.Collections.Generic;
using System.Text.Json;

namespace Amogus
{
    [HarmonyPatch(typeof(ShipStatus), nameof(ShipStatus.FixedUpdate))]
    public static class StateExportPatch
    {
        static int tickCounter = 0;
        const int EXPORT_INTERVAL = 5;

        public static void Postfix(ShipStatus __instance)
        {
            if (ShipStatus.Instance == null) return;

            tickCounter++;
            if (tickCounter < EXPORT_INTERVAL) return;
            tickCounter = 0;

            var gameState = new Dictionary<string, object>();

            foreach (PlayerControl player in PlayerControl.AllPlayerControls)
            {
                if (player == null || player.Data == null) continue;

                gameState[player.Data.PlayerName] = new
                {
                    x = player.transform.position.x,
                    y = player.transform.position.y,
                    isDead = player.Data.IsDead,
                    isImpostor = player.Data.Role.IsImpostor
                };
            }

            string jsonPayload = JsonSerializer.Serialize(gameState);
            WebSocketManager.Send(jsonPayload);
        }
    }
}