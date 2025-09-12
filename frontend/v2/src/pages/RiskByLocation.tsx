import { useState } from "react";
import TopNav from "@/components/TopNav";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { analyzeCity } from "@/lib/api";

type CompanyRow = {
  company_name: string;
  sustainability_score?: number;
  esg_rating?: string;
  environmental_score?: number;
  social_score?: number;
  governance_score?: number;
  industry?: string | null;
  location?: string | null;
  summary?: string;
};

type CityRankingsResponse = {
  city: string;
  companies: CompanyRow[];
  discovery_html?: string;
  analysis_summary?: Record<string, any>;
  timestamp: string;
  total_analyzed: number;
};

/** Small helper so summaries don't get cut off permanently. */
function SummaryCell({
  text,
  initialChars = 200,
}: {
  text?: string;
  initialChars?: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!text || text.trim().length === 0) {
    return <span className="text-muted-foreground">—</span>;
  }

  const needsClamp = text.length > initialChars;
  const display =
    expanded || !needsClamp ? text : text.slice(0, initialChars).trimEnd() + "…";

  return (
    <div>
      <p className="text-sm leading-6 whitespace-pre-line break-words">
        {display}
      </p>
      {needsClamp && (
        <button
          type="button"
          className="text-blue-600 hover:underline text-xs mt-1"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

export default function RiskByLocation() {
  const [city, setCity] = useState("London");
  const [topN, setTopN] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [discoveryHtml, setDiscoveryHtml] = useState<string | null>(null);
  const [companies, setCompanies] = useState<CompanyRow[] | null>(null);
  const [summary, setSummary] = useState<Record<string, any> | null>(null);

  async function onAnalyze() {
    setLoading(true);
    setError(null);
    setDiscoveryHtml(null);
    setCompanies(null);
    setSummary(null);

    try {
      const data = (await analyzeCity(city, topN)) as CityRankingsResponse;

      if (!data || (!data.discovery_html && (!data.companies || data.companies.length === 0))) {
        setError("No results for that city.");
        return;
      }

      setDiscoveryHtml(data.discovery_html || null);
      setCompanies(data.companies || []);
      setSummary(data.analysis_summary || null);
    } catch (e: any) {
      setError(e?.message || "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <TopNav />
      <main className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Compare by location</h1>

        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_120px] gap-3 items-end mb-6">
          <div>
            <Label htmlFor="city">City</Label>
            <Input
              id="city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="companies">Companies</Label>
            <Input
              id="companies"
              type="number"
              min={3}
              max={20}
              value={topN}
              onChange={(e) => setTopN(parseInt(e.target.value || "10", 10))}
            />
          </div>
          <Button onClick={onAnalyze} disabled={loading}>
            {loading ? "Analyzing…" : "Analyze"}
          </Button>
        </div>

        {!!error && (
          <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 mb-6">
            {error}
          </div>
        )}

        {!!discoveryHtml && (
          <Card className="mb-6">
            <CardContent className="prose max-w-none p-4">
              <div dangerouslySetInnerHTML={{ __html: discoveryHtml }} />
            </CardContent>
          </Card>
        )}

        {!!summary && (
          <Card className="mb-6">
            <CardContent className="p-4">
              <h2 className="text-xl font-semibold mb-2">Analysis Summary</h2>
              <div className="text-sm grid gap-1">
                {"average_sustainability_score" in summary && (
                  <div>
                    <span className="font-medium">Average score: </span>
                    {summary.average_sustainability_score}
                  </div>
                )}
                {"top_performer" in summary && (
                  <div>
                    <span className="font-medium">Top performer: </span>
                    {summary.top_performer} ({summary.top_score})
                  </div>
                )}
                {"companies_with_good_scores" in summary && (
                  <div>
                    <span className="font-medium">Companies ≥ 65: </span>
                    {summary.companies_with_good_scores}
                  </div>
                )}
                {"companies_with_poor_scores" in summary && (
                  <div>
                    <span className="font-medium">Companies &lt; 50: </span>
                    {summary.companies_with_poor_scores}
                  </div>
                )}
                {"most_common_industry" in summary && (
                  <div>
                    <span className="font-medium">Most common industry: </span>
                    {summary.most_common_industry}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {!!companies && companies.length > 0 && (
          <Card>
            <CardContent className="p-0 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted">
                  <tr>
                    <th className="text-left p-3">Company</th>
                    <th className="text-left p-3">Industry</th>
                    <th className="text-left p-3">Sustainability</th>
                    <th className="text-left p-3">ESG Rating</th>
                    <th className="text-left p-3">E</th>
                    <th className="text-left p-3">S</th>
                    <th className="text-left p-3">G</th>
                    <th className="text-left p-3">Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {companies.map((c, i) => (
                    <tr key={`${c.company_name}-${i}`} className="border-t">
                      <td className="p-3 font-medium">{c.company_name}</td>
                      <td className="p-3">{c.industry || "—"}</td>
                      <td className="p-3">
                        {typeof c.sustainability_score === "number"
                          ? c.sustainability_score.toFixed(1)
                          : "—"}
                      </td>
                      <td className="p-3">{c.esg_rating || "—"}</td>
                      <td className="p-3">
                        {typeof c.environmental_score === "number"
                          ? c.environmental_score.toFixed(1)
                          : "—"}
                      </td>
                      <td className="p-3">
                        {typeof c.social_score === "number"
                          ? c.social_score.toFixed(1)
                          : "—"}
                      </td>
                      <td className="p-3">
                        {typeof c.governance_score === "number"
                          ? c.governance_score.toFixed(1)
                          : "—"}
                      </td>
                      <td className="p-3 align-top">
                        <SummaryCell text={c.summary} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </main>
    </>
  );
}
