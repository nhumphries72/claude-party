using UnityEngine;

namespace Amogus
{
    public static class SabotageProcessor
    {
        public static void ProcessCommand(BotCommand cmd)
        {
            PlayerControl bot = Plugin.IDToBot(cmd.bot_id);
            if (bot == null || bot.Data.IsDead) return;

            switch (cmd.sub_action)
            {
                case "start":
                    switch (cmd.system)
                    {
                        case "o2":
                            Plugin.Instance.Log.LogInfo($"Bot {cmd.bot_id} triggered an oxygen sabotage");
                            ShipStatus.Instance.RpcUpdateSystem(SystemTypes.LifeSupp, 16);
                        break;
                    }
                break;
            }
        }
    }
}