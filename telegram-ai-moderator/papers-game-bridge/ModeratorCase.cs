namespace PapersTelegramBridge;

public sealed class ModeratorCase {
    public long Id { get; set; }
    public long ChatId { get; set; }
    public long UserId { get; set; }
    public string Category { get; set; } = "";
    public string Reason { get; set; } = "";
    public double Score { get; set; }
    public ModeratorUser User { get; set; } = new();
    public List<ModeratorMessage> Messages { get; set; } = new();
}

public sealed class ModeratorUser {
    public string? Username { get; set; }
    public string? DisplayName { get; set; }
    public string? FirstSeenAt { get; set; }
    public string? JoinedAt { get; set; }
    public long MessageCount { get; set; }
    public int Warnings { get; set; }
    public int Cases { get; set; }
    public string? PhotoUrl { get; set; }
}

public sealed class ModeratorMessage {
    public long MessageId { get; set; }
    public string Text { get; set; } = "";
    public string CreatedAt { get; set; } = "";
}