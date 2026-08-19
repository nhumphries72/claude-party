using UnityEngine;
using System.Globalization;
using Il2CppSystem.Collections.Generic;

namespace Amogus
{
    public static class OnMatchStartFunctions
    {
        public static bool botsSanitized = false;
        public static void Initialize()
        {
            Plugin.OnMatchStart += SanitizeBots;
            Plugin.OnMatchStart += SendTasks;
        }

        private static void SanitizeBots()
        {
            if (ShipStatus.Instance != null && !botsSanitized)
                {
                    if (PlayerControl.AllPlayerControls != null && PlayerControl.AllPlayerControls.Count > 1)
                    {
                        Plugin.Instance.Log.LogInfo($"Found {PlayerControl.AllPlayerControls.Count} players. Beginning sweep.");

                        foreach (var player in PlayerControl.AllPlayerControls)
                        {
                            if (player != null && PlayerControl.LocalPlayer != null)
                            {
                                if (!Plugin.IsLocalPlayer(player))
                                {
                                    Plugin.Instance.Log.LogInfo($"Target acquired: Bot {player.PlayerId}");
                                    
                                    player.enabled = false;
                                    Plugin.Instance.Log.LogInfo("Disabled PlayerControl script");
                                    
                                    var light = player.GetComponentInChildren<LightSource>();
                                    if (light != null)
                                    {
                                        Plugin.Instance.Log.LogInfo("Disabling light");
                                        light.enabled = false;
                                    }
                                    else
                                    {
                                        Plugin.Instance.Log.LogInfo("Child light component is null");
                                    }

                                    if (player.Data?.Role != null)
                                    {
                                        player.Data.Role.enabled = false;
                                        Plugin.Instance.Log.LogInfo($"Disabled {player.Data.Role.Role} script");
                                    }
                                    else
                                    {
                                        Plugin.Instance.Log.LogInfo($"player.Data == null: {player.Data == null} \nplayer.Data.Role == null: {player.Data?.Role == null}");
                                    }
                                }
                            }
                        }
                        
                        Plugin.Instance.Log.LogInfo("Sweep complete.");

                        if (PlayerControl.LocalPlayer.Data.Role.IsImpostor)
                        {
                            if (HudManager.Instance != null)
                            {
                                if (HudManager.Instance.KillButton != null) 
                                {
                                    HudManager.Instance.KillButton.gameObject.SetActive(true);
                                    Plugin.Instance.Log.LogInfo("Revived kill button");
                                }
                                if (HudManager.Instance.SabotageButton != null) 
                                {
                                    HudManager.Instance.SabotageButton.gameObject.SetActive(true);
                                    Plugin.Instance.Log.LogInfo("Revived sabotage button");
                                }
                                if (HudManager.Instance.ImpostorVentButton != null)
                                {
                                    HudManager.Instance.ImpostorVentButton.gameObject.SetActive(true);
                                    Plugin.Instance.Log.LogInfo("Revived vent button");
                                }
                            }
                        }

                        botsSanitized = true;
                    }
                }
            else if (ShipStatus.Instance == null && botsSanitized)
            {
                Plugin.Instance.Log.LogInfo("Setting botsSanitized to false");
                botsSanitized = false;
            }
        }

        public static void SendTasks()
        {
            string payloadStr = "{\"type\": \"init_tasks\", \"assignments\": {";
            bool firstPlayer = true;

            foreach (var player in PlayerControl.AllPlayerControls)
            {
                if (!firstPlayer) payloadStr += ",";
                payloadStr += $"\"{player.PlayerId}\": [";

                bool firstTask = true;
                foreach (var task in player.myTasks)
                {
                    if (!firstTask) payloadStr += ",";
                    string cleanName = task.name.Replace("(Clone)", "").Trim();
                    if (cleanName != "T")
                    {
                        payloadStr += $"{{\"task\": \"{cleanName}\", \"room\": \"{task.StartAt}\"";

                        List<Vector2> locations = null;
                        try
                        {
                            locations = task.Locations;
                        }
                        catch { }

                        if (locations != null)
                        {
                            for (int i = 0; i < locations.Count; i++)
                            {
                                if (i > 0) payloadStr += ",";
                                var pos = locations[i];
                                string x = pos.x.ToString(CultureInfo.InvariantCulture); string y = pos.y.ToString(CultureInfo.InvariantCulture);
                                payloadStr += $", \"location\": {{\"x\": {x}, \"y\": {y}}}";
                            }
                        }
                        payloadStr += "}";
                        firstTask = false;
                    }
                }
                payloadStr += "]";
                firstPlayer = false;
            }

            payloadStr += "}}";

            WebSocketManager.Send(payloadStr);
        }
    }
}