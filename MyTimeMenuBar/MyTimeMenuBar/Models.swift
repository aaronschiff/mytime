import Foundation

enum AppDefaults {
    /// Fallback server URL when nothing has been saved to UserDefaults yet.
    static let serverBaseURL = "http://mytime.local:8000"
}

struct ProjectRef: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
}

struct TaskTypeRef: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
}

struct Entry: Codable, Identifiable {
    let id: Int
    let projectId: Int
    let projectName: String
    let taskTypeId: Int
    let taskTypeName: String
    let notes: String
    let baseSeconds: Int
    let running: Bool
    let since: String?   // UTC ISO8601 + "Z", or nil when stopped
    let locked: Bool

    /// The `since` timestamp parsed to a `Date`, or nil when the entry is stopped.
    var sinceDate: Date? {
        guard let since else { return nil }
        return Entry.parseTimestamp(since)
    }

    /// Parse the backend's timestamp: Python `datetime.isoformat()` of a naive
    /// UTC instant with "Z" appended, e.g. "2026-07-05T13:45:00.123456Z"
    /// (6-digit microseconds) or "2026-07-05T13:45:00Z". `ISO8601DateFormatter`
    /// is unreliable with 6 fractional digits, so parse the whole-second UTC
    /// instant directly — sub-second precision is irrelevant for a
    /// seconds-resolution timer.
    static func parseTimestamp(_ s: String) -> Date? {
        var body = s
        if body.hasSuffix("Z") { body.removeLast() }
        if let dot = body.firstIndex(of: ".") { body = String(body[..<dot]) }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = TimeZone(identifier: "UTC")
        f.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return f.date(from: body)
    }
}

struct TodayState: Codable {
    let day: String
    let totalSeconds: Int
    let weekSeconds: Int
    let projects: [ProjectRef]
    let taskTypes: [TaskTypeRef]
    let entries: [Entry]
}
