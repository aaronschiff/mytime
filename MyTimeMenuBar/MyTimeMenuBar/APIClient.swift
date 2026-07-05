import Foundation

enum APIError: LocalizedError {
    case message(String)
    var errorDescription: String? {
        if case .message(let m) = self { return m }
        return nil
    }
}

struct APIClient {
    var baseURL: String

    private static let jsonDecoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    // MARK: Endpoints

    func fetchToday() async throws -> TodayState {
        try await request("/api/today", method: "GET", body: nil)
    }

    func createEntry(projectId: Int, taskTypeId: Int, notes: String,
                     start: Bool, duration: String) async throws -> TodayState {
        try await request("/api/today/entries", method: "POST", body: [
            "project_id": projectId, "task_type_id": taskTypeId,
            "notes": notes, "start": start, "duration": duration,
        ])
    }

    func start(id: Int) async throws -> TodayState {
        try await request("/api/today/\(id)/start", method: "POST", body: nil)
    }

    func stop(id: Int) async throws -> TodayState {
        try await request("/api/today/\(id)/stop", method: "POST", body: nil)
    }

    func setTime(id: Int, timeHM: String) async throws -> TodayState {
        try await request("/api/today/\(id)/set-time", method: "POST",
                          body: ["time_hm": timeHM])
    }

    func edit(id: Int, projectId: Int, taskTypeId: Int,
              duration: String, notes: String) async throws -> TodayState {
        try await request("/api/today/\(id)/edit", method: "POST", body: [
            "project_id": projectId, "task_type_id": taskTypeId,
            "duration": duration, "notes": notes,
        ])
    }

    func delete(id: Int) async throws -> TodayState {
        try await request("/api/today/\(id)", method: "DELETE", body: nil)
    }

    // MARK: Core

    private func request(_ path: String, method: String,
                         body: [String: Any]?) async throws -> TodayState {
        let trimmed = baseURL.trimmingCharacters(in: .whitespaces)
        guard let url = URL(string: trimmed + path) else {
            throw APIError.message("Invalid server URL in Settings.")
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }

        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await URLSession.shared.data(for: req)
        } catch {
            throw APIError.message("Can't reach the server. Check it's running and the address in Settings.")
        }

        guard let http = response as? HTTPURLResponse else {
            throw APIError.message("Unexpected server response.")
        }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.message(Self.errorMessage(from: data, status: http.statusCode))
        }
        do {
            return try Self.jsonDecoder.decode(TodayState.self, from: data)
        } catch {
            throw APIError.message("Couldn't read the server response.")
        }
    }

    /// Normalize both error shapes into one message:
    ///   router:       {"error": "..."}
    ///   FastAPI 422:  {"detail": [{"msg": "..."}, ...]}  or  {"detail": "..."}
    static func errorMessage(from data: Data, status: Int) -> String {
        if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
            if let msg = obj["error"] as? String { return msg }
            if let detail = obj["detail"] as? String { return detail }
            if let detail = obj["detail"] as? [[String: Any]] {
                let msgs = detail.compactMap { $0["msg"] as? String }
                if !msgs.isEmpty { return msgs.joined(separator: "; ") }
            }
        }
        return "Request failed (HTTP \(status))."
    }
}
