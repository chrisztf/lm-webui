export async function startRun(sessionId: string, type: "local" | "api", payload: any) {
  const res = await fetch("/api/run/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, type, ...payload })
  });
  return res.json();
}

export async function stopRun(sessionId: string) {
  const res = await fetch("/api/run/stop", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId })
  });
  return res.json();
}

export async function getStatus(sessionId: string) {
  const res = await fetch(`/api/run/status?session_id=${encodeURIComponent(sessionId)}`);
  return res.json();
}
