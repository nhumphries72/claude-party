using AmongUs.GameOptions;
using HarmonyLib;
using InnerNet;
using Mono.Cecil.Cil;
using RewiredConsts;
using UnityEngine;

namespace Amogus
{
    [HarmonyPatch(typeof(AmongUsClient), nameof(AmongUsClient.Update))]
    public static class DeveloperHotkeyPatch
    {
        private static byte _botIdCounter = 1;
        private static bool _isBridgeConnected = false;
        public static bool botsSanitized = false;
        public static bool isCircling = false;
        public static float circleTimer = 0f;
        public static void Postfix(AmongUsClient __instance)
        {
            if (PlayerControl.LocalPlayer != null && PlayerControl.LocalPlayer.PlayerId > 0)
            {
                foreach (var p in Object.FindObjectsOfType<PlayerControl>())
                {
                    if (p.PlayerId == 0)
                    {
                        PlayerControl.LocalPlayer = p;

                        var cam = Camera.main?.GetComponent<FollowerCamera>();
                        cam?.SetTarget(p);
                        
                        Plugin.Instance.Log.LogInfo("Reverted LocalPlayer to player 0");
                        break;
                    }
                }  
            }

            if (Input.GetKeyDown(KeyCode.F5))
            {
                try
                {
                    PlayerControl humanPlayer = PlayerControl.LocalPlayer;

                    if (_botIdCounter > 14) return;

                    byte botPlayerId = _botIdCounter++;
                    PlayerControl botBody = Object.Instantiate(AmongUsClient.Instance.PlayerPrefab);
                    botBody.transform.position = humanPlayer.transform.position;

                    botBody.OwnerId = AmongUsClient.Instance.ClientId;
                    botBody.NetId = (uint)(botPlayerId * 1000);
                    botBody.PlayerId = botPlayerId;

                    botBody.isDummy = true;
                    botBody.notRealPlayer = true;
                    botBody.hasBeenSerialized = true;

                    AmongUsClient.Instance.AddNetObject(botBody);

                    var client = AmongUsClient.Instance.GetClient(AmongUsClient.Instance.ClientId);
                    NetworkedPlayerInfo botData = GameData.Instance.AddPlayer(botBody, client);

                    if (botData != null)
                    {
                        botData.DefaultOutfit.ColorId = 0;
                        if (botData.Outfits != null && botData.Outfits.Count > 0)
                        {
                            botData.Outfits[0].ColorId = 0;
                        }

                        botData.DefaultOutfit.NamePlateId = "nameplate_NoPlate";

                        botBody.SetColor(botPlayerId);
                        botData.PlayerName = "Claude " + botPlayerId;
                    }

                    PlayerControl.LocalPlayer = humanPlayer;

                    Plugin.Instance.Log.LogInfo($"Spawned {botData.PlayerName}");

                    if (!_isBridgeConnected)
                    {
                        WebSocketManager.Connect();
                        _isBridgeConnected = true;
                    }
                }
                catch (System.Exception e)
                {
                    Plugin.Instance.Log.LogError($"Spawn failed: {e.Message}\n{e.StackTrace}");
                }
            }

            if (Input.GetKeyDown(KeyCode.F6))
            {
                string payload = $"{{\"type\": \"location\", \"current_location\": [{PlayerControl.LocalPlayer.transform.position.x}, {PlayerControl.LocalPlayer.transform.position.y}]}}";
                WebSocketManager.Send(payload);
            }

            if (Input.GetKeyDown(KeyCode.F8))
            {
                Plugin.Instance.Log.LogInfo("\nAPI Scan: IntroCutscene");
                foreach (var method in typeof(IntroCutscene).GetMethods(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static))
                {
                    string parameters = "";
                    foreach (var param in method.GetParameters())
                    {
                        parameters += $"{param.ParameterType.Name} {param.Name}, ";
                    }
                    Plugin.Instance.Log.LogInfo($"[METHOD] {method.ReturnType.Name} {method.Name}({parameters})");
                }
            }

            if (Input.GetKeyDown(KeyCode.F9))
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

            if (Input.GetKeyDown(KeyCode.F10))
            {
                isCircling = !isCircling;
                Plugin.Instance.Log.LogInfo($"Movement test: {isCircling}");

                if (!isCircling && PlayerControl.AllPlayerControls != null)
                {
                    foreach (var player in PlayerControl.AllPlayerControls)
                    {
                        if (player != null)
                        {
                            var body = player.GetComponent<Rigidbody2D>();
                            body?.velocity = Vector2.zero;
                        }
                    }
                }
            }

            if (isCircling && ShipStatus.Instance != null && PlayerControl.AllPlayerControls != null)
            {
                circleTimer += Time.deltaTime;

                int botCount = 0;
                foreach (var p in PlayerControl.AllPlayerControls)
                {
                    if (p != null) botCount++;
                }

                if (botCount > 0)
                {
                    int botIndex = 0;
                    float radius = 2.5f;
                    float orbitSpeed = 2.0f;

                    foreach (var player in PlayerControl.AllPlayerControls)
                    {
                        if (player != null)
                        {
                            float angle = (circleTimer * orbitSpeed) + (botIndex * (Mathf.PI * 2f / botCount));
                            Vector2 targetPos = new(
                                PlayerControl.LocalPlayer.transform.position.x + Mathf.Cos(angle) * radius,
                                PlayerControl.LocalPlayer.transform.position.y + Mathf.Sin(angle) * radius
                            );

                            Vector2 currentPos = player.transform.position;
                            Vector2 direction = targetPos - currentPos;

                            var body = player.GetComponent<Rigidbody2D>();
                            body?.velocity = direction * 10f;
                        }
                        botIndex++;
                    }
                }
            }
        }
    }
}