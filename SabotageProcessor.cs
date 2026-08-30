using UnityEngine;

namespace Amogus
{
    public static class SabotageProcessor
    {
        public static void ProcessCommand(BotCommand cmd)
        {
            if (ShipStatus.Instance == null) return;

            PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
            if (bot == null || bot.Data.IsDead) return;
            byte consoleByte = 0;

            switch (cmd.sub_action)
            {
                case "start":
                    switch (cmd.system)
                    {
                        case "o2":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} triggered an oxygen sabotage");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)8);
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.LifeSupp, (byte)128);
                        break;
                        case "reactor":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} triggered a reactor meltdown");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)3);
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Reactor, (byte)128);
                        break;
                        case "lights":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} triggered a lighting sabotage");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)7);
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Electrical, (byte)135);
                        break;
                        case "comms":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} triggered a communications sabotage");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Sabotage, (byte)14);
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Comms, (byte)128);
                        break;
                        case "doors":
                            if (System.Enum.TryParse(cmd.room, true, out SystemTypes roomType))
                            {
                                ShipStatus.Instance.RpcCloseDoorsOfType(roomType);
                            }
                        break;
                    }
                    string roomName = cmd.system == "doors" ? cmd.room : "none";
                    string payload = $"{{\"type\": \"event\", \"event_type\": \"sabotage_successful\", \"bot_id\": {cmd.bot_id}, \"system\": \"{cmd.system}\", \"room\": \"{roomName}\"}}";
                    WebSocketManager.Send(payload);
                break;
                case "fix":
                    switch (cmd.system)
                    {
                        case "o2":
                            consoleByte = cmd.panel == "admin" ? (byte)65 : (byte)64;
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} fixing {cmd.panel} panel");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.LifeSupp, consoleByte);
                        break;
                        case "reactor":
                            consoleByte = cmd.panel == "top" ? (byte)64 : (byte)65;
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} fixing {cmd.panel} panel");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Reactor, consoleByte);
                        break;
                        case "lights":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} fixing lights");
                            
                            if (ShipStatus.Instance.Systems.ContainsKey(SystemTypes.Electrical))
                            {
                                var electricalSystem = ShipStatus.Instance.Systems[SystemTypes.Electrical].Cast<SwitchSystem>();
                                if (electricalSystem != null)
                                {
                                    for (byte i = 0; i < 5; i++)
                                    {
                                        int expectedBit = (electricalSystem.ExpectedSwitches >> i) & 1;
                                        int actualBit = (electricalSystem.ActualSwitches >> i) & 1;

                                        if (expectedBit != actualBit)
                                        {
                                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Electrical, i);
                                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} flipped light switch {i}");
                                        }
                                    }
                                }
                            }
                        break;
                        case "comms":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} fixing communications");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.Comms, (byte)0);
                        break;
                    }
                    payload = $"{{\"type\": \"event\", \"event_type\": \"fix_successful\", \"bot_id\": {cmd.bot_id}, \"system\": \"{cmd.system}\", \"panel\": \"{cmd.panel}\"}}";
                    WebSocketManager.Send(payload);
                break;
            }
        }
    }
}