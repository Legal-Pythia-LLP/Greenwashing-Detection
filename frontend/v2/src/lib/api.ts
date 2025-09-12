const BASE =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, "") ||
  "http://localhost:8000";

export async function analyzeCity(city: string, topN = 10) {
  const res = await fetch(`${BASE}/v2/city-rankings/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ city, top_n: topN }), // IMPORTANT: top_n (snake_case)
  });

  const text = await res.text(); // better error messages
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} – ${text || "request failed"}`);
  }
  return JSON.parse(text);
}
