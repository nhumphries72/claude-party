using System;
using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Text.Json;
using System.Reflection;

namespace Amogus
{
    [Serializable]
    public class BotCommand
    {
        public string type {get; set;}
        public string action {get; set;}
        public byte bot_id {get; set;}
        public float x {get; set;}
        public float y {get; set;}
        public string task_name {get; set;}
        public int target_id {get; set;}
        public string sub_action {get; set;}
        public string system {get; set;}
        public string panel {get; set;}
        public string room {get; set;}
        public string message {get; set;}
        public int vent_id {get; set;}
    }

    [Serializable]
    public class TelemetryPayload
    {
        public string player_name;
        public float x;
        public float y;
    }

    public static class WebSocketManager
    {
        private static readonly Uri _serverUri = new("ws://localhost:8765");
        public static readonly ConcurrentQueue<Action> MainThreadQueue = new();

        private static ConcurrentQueue<string> _messageQueue = new();
        private static CancellationTokenSource _masterCts = new();

        public static void Connect()
        {
            Task.Run(async () =>
            {
                while (!_masterCts.IsCancellationRequested)
                {
                    using (var localCts = new CancellationTokenSource())
                    using (var ws = new ClientWebSocket())
                    {
                        try
                        {
                            await ws.ConnectAsync(_serverUri, CancellationToken.None);
                            Plugin.Instance.Log.LogInfo("Connected to moderator");

                            var listenTask = ListenPump(ws, localCts.Token);
                            var sendTask = SendPump(ws, localCts.Token);

                            await Task.WhenAny(listenTask, sendTask);

                            localCts.Cancel();
                            ws.Abort();
                        }
                        catch (Exception ex)
                        {
                            Plugin.Instance.Log.LogInfo($"WebSockets error: {ex.Message}");
                        }
                    }
                    Plugin.Instance.Log.LogInfo("Disconnected from moderator");
                    await Task.Delay(3000, _masterCts.Token);
                }
            });
        }

        public static void Send(string message)
        {
            _messageQueue.Enqueue(message);
        }

        private static async Task SendPump(ClientWebSocket ws, CancellationToken token)
        {
            while (ws.State == WebSocketState.Open && !token.IsCancellationRequested)
            {
                if (_messageQueue.TryDequeue(out string message))
                {
                    try
                    {
                        var bytes = Encoding.UTF8.GetBytes(message);
                        var buffer = new ArraySegment<byte>(bytes);
                        await ws.SendAsync(buffer, WebSocketMessageType.Text, true, token);
                    }
                    catch (Exception ex)
                    {
                        Plugin.Instance.Log.LogInfo($"WebSockets error: {ex.Message}");
                        break;
                    }
                }
                else
                {
                    try { await Task.Delay(10, token); }
                    catch (TaskCanceledException) { break; }
                }
            }
        }

        private static async Task ListenPump(ClientWebSocket ws, CancellationToken token)
        {
            var buffer = new byte[1024 * 4];

            while (ws.State == WebSocketState.Open && !token.IsCancellationRequested)
            {
                try
                {
                    var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), token);

                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, string.Empty, CancellationToken.None);
                        break;
                    }

                    string message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                    BotCommand cmd = JsonSerializer.Deserialize<BotCommand>(message);

                    if (cmd != null && cmd.type == "command")
                    {
                        CommandProcessor.ProcessCommand(cmd);
                    }
                }
                catch (Exception ex)
                {
                    Plugin.Instance.Log.LogError($"WebSockets error: {ex.Message}");
                    continue;
                }
            }
        }
    }
}