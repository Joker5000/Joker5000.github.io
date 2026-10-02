using System.Net.Http.Json;
using System.Text.Json;

namespace PapersTelegramBridge;

public sealed class BridgeClient {
    private readonly HttpClient http;
    private readonly JsonSerializerOptions json = new() { PropertyNameCaseInsensitive = true };

    public BridgeClient(string baseUrl, string token) {
        http = new HttpClient { BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/") };
        http.DefaultRequestHeaders.Add("X-Game-Bridge-Token", token);
        http.Timeout = TimeSpan.FromSeconds(10);
    }

    public async Task<ModeratorCase?> NextCaseAsync() {
        using var response = await http.GetAsync("api/game/next");
        response.EnsureSuccessStatusCode();
        using var stream = await response.Content.ReadAsStreamAsync();
        using var doc = await JsonDocument.ParseAsync(stream);
        var item = doc.RootElement.GetProperty("case");
        if (item.ValueKind == JsonValueKind.Null) return null;
        return item.Deserialize<ModeratorCase>(json);
    }

    public async Task<bool> DecisionAsync(long caseId, string action) {
        using var response = await http.PostAsJsonAsync($"api/game/case/{caseId}/decision", new { action });
        return response.IsSuccessStatusCode;
    }
}