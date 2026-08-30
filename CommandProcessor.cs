using System.Linq;
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

                        string payload = $"{{\"type\": \"event\", \"event_type\": \"emergency_meeting\", \"bot_id\": {cmd.bot_id}}}";
                        WebSocketManager.Send(payload);
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
                        DeadBody[] bodies = Object.FindObjectsOfType<DeadBody>(); 
                        VisionContainer vision = BotVision.GetVisibleEntitites(bot, bodies);

                        if (vision.VisibleCorpses.Count > 0)
                        {
                            DeadBody bodyToReport = vision.VisibleCorpses[0];
                            NetworkedPlayerInfo deadPlayerInfo = GameData.Instance.GetPlayerById(bodyToReport.ParentId);

                            if (deadPlayerInfo != null)
                            {
                                Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} reporting bot {bodyToReport.ParentId}'s body");
                                bot.CmdReportDeadBody(deadPlayerInfo);

                                string payload = $"{{\"type\": \"event\", \"event_type\": \"report\", \"bot_id\": {cmd.bot_id}, \"victim_id\": {bodyToReport.ParentId}}}";
                                WebSocketManager.Send(payload);
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
                case "chat":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
                        if (bot == null) return;

                        if (HudManager.Instance?.Chat != null)
                        {
                            HudManager.Instance.Chat.AddChat(bot, cmd.message);
                            
                            if (MeetingHud.Instance != null && !HudManager.Instance.Chat.IsOpenOrOpening)
                            {
                                HudManager.Instance.Chat.Toggle();
                            }

                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} sent a message");
                            string payload = $"{{\"type\": \"event\", \"event_type\": \"message\", \"bot_id\": {cmd.bot_id}, \"content\": {cmd.message}}}";
                            WebSocketManager.Send(payload);
                        }
                    });
                    break;
                case "vote":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
                        if (bot == null || bot.Data.IsDead || MeetingHud.Instance == null) return;

                        byte voteTarget = cmd.target_id == 15 ? (byte)253 : cmd.target_id;

                        MeetingHud.Instance.CmdCastVote(cmd.bot_id, voteTarget);

                        string payload = $"{{\"type\": \"event\", \"event_type\": \"vote\", \"bot_id\": {cmd.bot_id}, \"target\": {cmd.target_id}}}";
                        WebSocketManager.Send(payload);

                    });
                    break;
                case "proceed":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                        if (MeetingHud.Instance == null) return;

                        if (HudManager.Instance.Chat.IsOpenOrOpening)
                        {
                            HudManager.Instance.Chat.Toggle();
                        }

                        MeetingHud.Instance.HandleProceed();
                        Plugin.Instance.Log.LogInfo($"Concluding meeting");

                        string payload = $"{{\"type\": \"event\", \"event_type\": \"end_meeting\"}}";
                        WebSocketManager.Send(payload);
                    });
                    break;
                case "vent":
                    WebSocketManager.MainThreadQueue.Enqueue(() =>
                    {
                       PlayerControl bot = Plugin.IDToBot(cmd.bot_id);

                       if (bot == null || bot.Data.IsDead) return;

                       string payload = "";

                       switch (cmd.sub_action)
                        {
                            case "enter":
                                bot.MyPhysics.RpcEnterVent(cmd.vent_id);
                                BotVision.WitnessCrime(bot, "enter_vent");

                                payload = $"{{\"type\": \"event\", \"event_type\": \"enter_vent\", \"bot_id\": {cmd.bot_id}, \"vent\": {cmd.vent_id}}}";
                            break;
                            case "move":
                                Vent targetVent = ShipStatus.Instance.AllVents.FirstOrDefault(v => v.Id == cmd.vent_id);
                                if (targetVent != null)
                                {
                                    if (bot.NetTransform != null)
                                    {
                                        bot.NetTransform.SnapTo(targetVent.transform.position);
                                    }
                                    else
                                    {
                                        bot.transform.position = targetVent.transform.position;
                                    }
                                }

                                payload = $"{{\"type\": \"event\", \"event_type\": \"vent_movement\", \"bot_id\": {cmd.bot_id}, \"vent\": {cmd.vent_id}}}";
                            break;
                            case "exit":
                                bot.MyPhysics.RpcExitVent(cmd.vent_id);
                                BotVision.WitnessCrime(bot, "exit_vent");

                                payload = $"{{\"type\": \"event\", \"event_type\": \"exit_vent\", \"bot_id\": {cmd.bot_id}, \"vent\": {cmd.vent_id}}}";
                            break;
                        }
                        WebSocketManager.Send(payload);
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

