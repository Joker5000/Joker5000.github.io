using HarmonyLib;
using data;
using play.day;

namespace PapersTelegramBridge;

[HarmonyPatch]
public static class CasePatches {
    private static StampApprovalKind? lastStamp;

    [HarmonyPrefix]
    [HarmonyPatch(typeof(BoothEnv), nameof(BoothEnv.makeNewTraveler))]
    private static void SelectCase() {
        Plugin.TakeCase();
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(TravelerName), "randomize")]
    private static bool ReplaceTravelerName(TravelerName __instance, ref TravelerName __result) {
        var c = Plugin.ActiveCase;
        if (c is null) return true;

        var display = string.IsNullOrWhiteSpace(c.User.DisplayName)
            ? (c.User.Username ?? $"User{c.UserId}")
            : c.User.DisplayName;

        var parts = display.Split(' ', StringSplitOptions.RemoveEmptyEntries);
        var first = parts.Length > 0 ? parts[0] : "Telegram";
        var last = parts.Length > 1 ? string.Join(" ", parts.Skip(1)) : $"#{c.UserId}";

        __result = new TravelerName(__instance.nameCycler, __instance.male, first, last);
        return false;
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(BoothEngine), "stampPaper", typeof(string), typeof(StampApprovalKind))]
    private static void CaptureStamp(string idWithIndex, StampApprovalKind approvalType) {
        if (Plugin.ActiveCase is not null) lastStamp = approvalType;
    }

    [HarmonyPrefix]
    [HarmonyPatch(typeof(BoothEngine), "handleEvent", typeof(EngineEvent))]
    private static void FinishDecision(EngineEvent @event) {
        if (@event != EngineEvent.PROCESSING_FINISH || Plugin.ActiveCase is null || lastStamp is null) return;

        var c = Plugin.ActiveCase;
        var action = lastStamp == StampApprovalKind.APPROVED ? "approved" : "denied";
        lastStamp = null;
        Plugin.ClearCase();

        _ = Task.Run(async () => {
            try {
                await Plugin.Bridge.DecisionAsync(c.Id, action);
            } catch (Exception ex) {
                Plugin.Logger.LogError("Failed to submit stamp decision: " + ex.Message);
            }
        });
    }
}