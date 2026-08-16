using System;
using HarmonyLib;
using RewiredConsts;

namespace Amogus
{
    
    [HarmonyPatch(typeof(IntroCutscene), nameof(IntroCutscene.OnDestroy))]
    public static class MatchStartInitPatch
    {
        public static void Postfix(IntroCutscene __instance)
        {
            if (PlayerControl.AllPlayerControls == null) return;

            Plugin.Instance.Log.LogInfo("Scraping bot tasks");

            foreach (var player in PlayerControl.AllPlayerControls)
            {
                if (player == null || Plugin.IsLocalPlayer(player)) continue;

                string roleName = "Crewmate";
                if (player.Data.Role.IsImpostor) roleName = "Impostor";

                string tasksJsonArray = "[";
                if (player.myTasks?.Count > 0)
                {
                    for (int i = 0; i < player.myTasks.Count; i++)
                    {
                        var task = player.myTasks[i];
                        if (task != null)
                        {
                            string taskName = task.TaskType.ToString();
                            string roomName = task.StartAt.ToString();
                            tasksJsonArray += $"{{\"name\": \"{taskName}\", \"room\": \"{roomName}\"}}";
                            if (i < player.myTasks.Count - 1) tasksJsonArray += ", ";
                        }
                    }
                    tasksJsonArray += "]";

                    string initPayload = $@"{{
                        ""type"": ""init"",
                        ""bot_id"": {player.PlayerId},
                        ""role"": ""{roleName}"",
                        ""tasks"": {tasksJsonArray}
                    }}";

                    WebSocketManager.Send(initPayload);
                }
            }
        }
    }

    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.Awake))]
    public static class EnumDumperPatch
    {
        public static void Postfix()
        {
            Plugin.Instance.Log.LogInfo("--- Dumping all tasks ---");
            foreach (var task in Enum.GetValues(typeof(TaskTypes)))
            {
                Plugin.Instance.Log.LogInfo(task.ToString());
            }

            Plugin.Instance.Log.LogInfo("--- Dumping all rooms ---");
            foreach (var room in Enum.GetValues(typeof(SystemTypes)))
            {
                Plugin.Instance.Log.LogInfo(room.ToString());
            }
        }
    }

}