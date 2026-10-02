using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using System.Reflection;

namespace PapersTelegramBridge;

[BepInPlugin("joker5000.papers.telegram", "Papers Telegram Moderator Bridge", "0.1.0")]
[BepInProcess("PapersPlease.exe")]
public sealed class Plugin : BasePlugin {
    internal static ManualLogSource Logger = null!;
    internal static BridgeClient Bridge = null!;
    internal static ModeratorCase? ActiveCase;
    internal static ModeratorCase? NextCase;

    private ConfigEntry<string> bridgeUrl = null!;
    private ConfigEntry<string> bridgeToken = null!;
    private readonly Harmony harmony = new("joker5000.papers.telegram");

    public override void Load() {
        Logger = Log;
        bridgeUrl = Config.Bind("Bridge", "Url", "https://YOUR-VM.example.com/", "Moderator bridge URL");
        bridgeToken = Config.Bind("Bridge", "Token", "", "GAME_BRIDGE_TOKEN from the VM .env");

        if (string.IsNullOrWhiteSpace(bridgeToken.Value)) {
            Log.LogError("Bridge token is empty.");
            return;
        }

        Bridge = new BridgeClient(bridgeUrl.Value, bridgeToken.Value);
        harmony.PatchAll(Assembly.GetExecutingAssembly());
        _ = PollCases();
        Log.LogInfo("Papers Telegram Moderator Bridge loaded.");
    }

    private static async Task PollCases() {
        while (true) {
            try {
                if (NextCase is null) NextCase = await Bridge.NextCaseAsync();
            } catch (Exception ex) {
                Logger.LogWarning("Bridge poll failed: " + ex.Message);
            }
            await Task.Delay(2000);
        }
    }

    internal static ModeratorCase? TakeCase() {
        ActiveCase = NextCase;
        NextCase = null;
        return ActiveCase;
    }

    internal static void ClearCase() => ActiveCase = null;
}