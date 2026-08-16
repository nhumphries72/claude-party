using UnityEngine;

namespace Amogus
{
    public static class CommandProcessor
    {
        public static void ProcessCommand(BotCommand cmd)
        {
            if (cmd == null || string.IsNullOrEmpty(cmd.action)) return;

            switch (cmd.action)
            {
                case "move":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        Plugin.ActiveNavigations[cmd.bot_id] = new Vector2(cmd.x, cmd.y);
                    });
                    break;
                case "stop":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        Plugin.PendingStops[cmd.bot_id] = true;
                    });
                    break;
                case "complete_task":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        HandleCompleteTask(cmd);
                    });
                    break;
                case "resend_tasks":
                    WebSocketManager.MainThreadQueue.Enqueue(OnMatchStartFunctions.SendTasks);
                    break;
                case "call_meeting":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
                        bot?.CmdReportDeadBody(null);
                    });
                    break;
                case "hunt":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        Plugin.ActiveHunts[cmd.bot_id] = cmd.target_id;
                    });
                    break;
                case "report":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
                        VisionContainer vision = BotVision.GetVisibleEntitites(bot);

                        if (vision.VisibleCorpses.Count > 0)
                        {
                            DeadBody bodyToReport = vision.VisibleCorpses[0];
                            NetworkedPlayerInfo deadPlayerInfo = GameData.Instance.GetPlayerById(bodyToReport.ParentId);

                            if (deadPlayerInfo != null)
                            {
                                Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} reporting bot {bodyToReport.ParentId}'s body");
                                bot.CmdReportDeadBody(deadPlayerInfo);   
                            }
                        }
                        else
                        {
                            Plugin.Instance.Log.LogInfo($"Report request denied; bot {cmd.bot_id} cannot see any bodies");
                        }
                    });
                    break;
                case "sabotage":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        SabotageProcessor.ProcessCommand(cmd);
                    });
                    break;
                default:
                    Plugin.Instance.Log.LogWarning($"Unknown command: {cmd.action}");
                    break;
            }
        }

        private static void HandleCompleteTask(BotCommand cmd)
        {
            PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
            if (bot == null)
            {
                Plugin.Instance.Log.LogWarning($"Bot {cmd.bot_id} not found");
                return;
            }

            if (bot.myTasks == null)
            {
                Plugin.Instance.Log.LogWarning($"Bot {cmd.bot_id} has no task list");
                return;
            }

            bool taskFound = false;
            foreach (var task in bot.myTasks)
            {
                string cleanName = task.name.Replace("(Clone)", "").Trim();
                if (cleanName == cmd.task_name)
                {
                    taskFound = true;
                    bot.RpcCompleteTask(task.Id);

                    string payload = $"{{\"type\": \"event\", \"event_type\": \"task_complete\", \"bot_id\": {cmd.bot_id}, \"task_name\": \"{cmd.task_name}\"}}";
                    WebSocketManager.Send(payload);
                    break;
                }
            }

            if (!taskFound)
            {
                Plugin.Instance.Log.LogWarning($"No matching task found for {cmd.task_name}");
            }
        }
    }
}

