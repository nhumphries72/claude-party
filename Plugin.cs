using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Text;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using Il2CppInterop.Runtime.Injection;
using Il2CppSystem.Runtime.Remoting.Messaging;
using UnityEngine;

namespace Amogus
{
    [BepInPlugin("com.nathan.amogus", "Amogus", "1.0.0")]
    public class Plugin: BasePlugin
    {
        public static Plugin Instance { get; private set; }
        private GameObject telemetryContainer;
        
        public static ConcurrentDictionary<byte, Vector2> ActiveNavigations = [];
        public static ConcurrentDictionary<byte, bool> PendingStops = [];
        public static ConcurrentDictionary<byte, byte> ActiveHunts = [];

        public static event Action OnMatchStart;
        public static event Action OnMatchEnded;

        public static void TriggerMatchLive() => OnMatchStart?.Invoke();
        public static void TriggerMatchEnded() => OnMatchEnded?.Invoke();

        public override void Load()
        {
            Instance = this;

            ClassInjector.RegisterTypeInIl2Cpp<TelemetryComponent>();
            Harmony.CreateAndPatchAll(typeof(Plugin).Assembly);
            Log.LogInfo("Amogus patches applied successfully.");

            OnMatchStartFunctions.Initialize();
            WebSocketManager.Connect();

            telemetryContainer = new GameObject("AmogusTelemetryBridge");
            UnityEngine.Object.DontDestroyOnLoad(telemetryContainer);
            telemetryContainer.hideFlags = HideFlags.HideAndDontSave;

            telemetryContainer.AddComponent<TelemetryComponent>();
        }

        public static string GetRoomName(Vector2 position)
        {
            if (ShipStatus.Instance?.FastRooms != null)
            {
                foreach (var kvp in ShipStatus.Instance.FastRooms)
                {
                    if (kvp.Value?.roomArea != null)
                    {
                        if (kvp.Value.roomArea.OverlapPoint(position)) return kvp.Key.ToString();
                    }
                }
            }
            return "None";
        }

        public static bool IsLocalPlayer(PlayerControl player)
        {
            return player.PlayerId == PlayerControl.LocalPlayer.PlayerId;
        }

        public static PlayerControl IDToBot(int bot_id)
        {
            bot_id = (byte)bot_id;
            foreach (var player in PlayerControl.AllPlayerControls)
            {
                if (player.PlayerId == bot_id)
                {
                    return player;
                }
            }
            return null;
        }
    }

    public class TelemetryComponent : MonoBehaviour
    {
        private float timer = 0f;
        private const float TargetInterval = 0.1f;
        private bool eventLock = false;

        private readonly StringBuilder telemetryBuilder = new(1024);

        private readonly Dictionary<byte, HashSet<int>> previousVisibleCorpses = [];

        public TelemetryComponent(IntPtr ptr): base(ptr) { }

        public void Start()
        {
            Plugin.Instance.Log.LogInfo("Telemetry component attached");
        }

        public void Update()
        {
            while (WebSocketManager.MainThreadQueue.TryDequeue(out var action))
            {
                try {
                    action?.Invoke();
                }
                catch (Exception ex)
                {
                    Plugin.Instance.Log.LogError($"Thread execution error: {ex.Message}");
                }
            }

            timer += Time.deltaTime;
            if (timer >= TargetInterval)
            {
                timer = 0f;
                ProcessTelemetry();
            }

            if (ShipStatus.Instance != null && !eventLock)
            {
                if (PlayerControl.AllPlayerControls?.Count > 1 && PlayerControl.LocalPlayer?.Data?.Role != null)
                {
                    if (PlayerControl.LocalPlayer.CanMove)
                    {
                        Plugin.Instance.Log.LogInfo("Match has begun");
                        eventLock = true;

                        Plugin.TriggerMatchLive();
                    }
                }
            }
            else if (ShipStatus.Instance == null && eventLock)
            {
                Plugin.Instance.Log.LogInfo("Match has ended");
                eventLock = false;

                Plugin.TriggerMatchEnded();
            }
        }

        private void ProcessTelemetry()
        {
            if (AmongUsClient.Instance == null || PlayerControl.AllPlayerControls == null) return;
            
            try
            {
                telemetryBuilder.Clear();
                telemetryBuilder.Append("{\"type\": \"telemetry\", \"players\": {");

                bool first = true;

                DeadBody[] allCorpses = FindObjectsOfType<DeadBody>();

                foreach (var player in PlayerControl.AllPlayerControls)
                {
                    if (player == null || player.Data == null) continue;
                    if (!first) telemetryBuilder.Append(',');

                    byte botId = player.PlayerId;
                    var pos = player.transform.position;
                    string roomName = Plugin.GetRoomName(pos);
                    string isImposter = player.Data.Role.IsImpostor ? "true": "false";
                    string alive = player.Data.IsDead ? "false": "true";

                    telemetryBuilder.Append($"\"{botId}\": {{\"x\": {pos.x:F2}, \"y\": {pos.y:F2}, \"room\": \"{roomName}\", \"imposter\": {isImposter}, \"alive\": {alive}}}");
                    first = false;

                    if (!player.Data.IsDead && !previousVisibleCorpses.ContainsKey(botId))
                    {
                        previousVisibleCorpses[botId] = [];
                    }

                    HashSet<int> currentlyVisible = [];
                    VisionContainer vision = BotVision.GetVisibleEntitites(player, allCorpses);

                    foreach (DeadBody body in vision.VisibleCorpses)
                    {
                        int bodyInstanceId = body.GetInstanceID();
                        currentlyVisible.Add(bodyInstanceId);

                        if (!previousVisibleCorpses[botId].Contains(bodyInstanceId))
                        {
                            string payload = $"{{\"type\": \"event\", \"event_type\": \"corpse_spotted\", \"bot_id\": {botId}, \"corpse_id\": {body.ParentId}}}";
                            WebSocketManager.Send(payload);
                        }
                    }
                    previousVisibleCorpses[botId] = currentlyVisible;
                }
                telemetryBuilder.Append("}}");

                WebSocketManager.Send(telemetryBuilder.ToString());
            }
            catch (Exception e)
            {
                Plugin.Instance.Log.LogError($"Telemetry error: {e.Message}");
            }
        }
    }
}