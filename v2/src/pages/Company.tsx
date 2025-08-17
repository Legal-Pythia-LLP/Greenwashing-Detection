import { useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import TopNav from "@/components/TopNav";
import Seo from "@/components/Seo";
import { FloatingChatbot } from "@/components/FloatingChatbot";
import { ResponsiveContainer, Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Tooltip } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { APIService } from "../services/api.service";

/**
 * Extracts the specified section from final_synthesis
 * @param text Full final_synthesis text
 * @param sectionNumber Section number to extract (2, 4, 5)
 * @returns Corresponding section content as a string (without the title)
 */
function extractSection(text: string, sectionNumber: number): string {
  if (!text || typeof text !== "string") return "";

  // Match **2. ... up to next **3. ... or end of text
  const regex = new RegExp(
    `\\*\\*${sectionNumber}\\.\\s[\\s\\S]*?(?=\\n\\n\\*\\*${sectionNumber + 1}\\.\\s|\\n\\n\\*\\*${sectionNumber + 2}\\.\\s|$)`,
    "i"
  );

  const match = text.match(regex);
  if (match) {
    // Remove "**2. ..." title
    return match[0]
      .replace(new RegExp(`^\\*\\*${sectionNumber}\\..*?\\*\\*`), "")
      .trim();
  }

  return "";
}

function parseFinalSynthesis(synthesis?: string) {
  if (!synthesis) return [];
  const sections = synthesis.split(/##\s+/).filter(Boolean);
  return sections.map(sec => {
    const [titleLine, ...rest] = sec.split("\n");
    return {
      title: titleLine.trim(),
      content: rest.join("\n").trim()
    };
  });
}

const mock = {
  acme: {
    name: "Acme Bank Holdings",
    score: 86,
    summary: "The company's sustainability report has high risk, mainly due to vague statements and lack of third-party verification.",
    breakdown: [
      { type: "Vague Statements", value: 85 },
      { type: "Lack of Metrics", value: 72 },
      { type: "Misleading Terms", value: 68 },
      { type: "Insufficient Third-Party Verification", value: 74 },
      { type: "Unclear Scope Definition", value: 61 },
    ],
    evidence: {
      "Vague Statements": [
        {
          quote: "We are committed to achieving carbon neutrality in the future.",
          why: "Lacks timeline and quantifiable metrics, making it a non-specific and unverifiable statement.",
        },
      ],
      "Lack of Metrics": [
        {
          quote: "Significantly reduced supply chain emissions.",
          why: "No baseline year, reduction magnitude, or coverage details provided.",
        },
      ],
    },
    external: [
      "Regulatory update: An agency is reviewing its environmental claims compliance.",
      "Industry news: Multiple banks updated their disclosure standards to meet new regulations.",
    ],
  },
};

const riskTone = (score: number) => {
  if (score >= 70) return "destructive";  // High risk - Red
  if (score >= 40) return "accent";       // Medium risk - Blue
  return "secondary";                      // Low risk - Gray
};

const Company = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const mockData = (mock as any)[id ?? "acme"] ?? (mock as any).acme;

  const { data: apiRes } = useQuery({
    queryKey: ["report", id],
    queryFn: async () => {
      if (!id) throw new Error("missing id");
      return await APIService.getReport(id);
    },
    enabled: !!id,
    retry: 0,
  });

  const viewLS = (() => {
    try {
      if (!id) return null;
      const raw = localStorage.getItem(`report:${id}`);
      if (!raw) return null;
      const d = JSON.parse(raw);
      return {
        name: d.company_name || "Unknown Company",
        score: Math.round(d.overall_score ?? 0),
        summary: d.summary ?? "",
        breakdown: (d.breakdown ?? []).map((x: any) => ({ type: x.type, value: Math.round(x.value ?? 0) })),
        evidenceGroups: d.evidence ?? [],
        final_synthesis: d.final_synthesis ?? d.response ?? "",
        external: d.external ?? [],
      };
    } catch {
      return null;
    }
  })();

const view = apiRes?.data
  ? {
      name: apiRes.data.company_name,
      final_synthesis: apiRes.data.final_synthesis ?? apiRes.data.response ?? "",
      score: (() => {
        try {
          if (apiRes.data.graphdata) {
            let graphdata = apiRes.data.graphdata;
            if (typeof graphdata === 'string') {
              let cleanData = graphdata.replace(/```json\n?/g, '').replace(/```/g, '').trim();
              try {
                graphdata = JSON.parse(cleanData);
              } catch {
                cleanData = cleanData.replace(/^\s*{\s*/, '{').replace(/\s*}\s*$/, '}');
                graphdata = JSON.parse(cleanData);
              }
            }
            const overallScore = graphdata.overall_greenwashing_score?.score ?? 0;
            return Math.round(overallScore * 10);
          }
          return Math.round(apiRes.data.overall_score ?? 0);
        } catch (e) {
          console.error('Failed to parse graphdata:', e);
          return Math.round(apiRes.data.overall_score ?? 0);
        }
      })(),
      summary: (() => {
        if (apiRes.data.final_synthesis) {
          const synthesis = apiRes.data.final_synthesis;
          const execSummaryMatch = synthesis.match(
            /\*\*1\. Executive Summary\*\*([\s\S]*?)(?=\n\n\*\*2\.)/
          );
          if (execSummaryMatch) {
            return execSummaryMatch[1].trim();
          }
          return synthesis.substring(0, 200) + "...";
        }
        return apiRes.data.summary ?? "No summary available";
      })(),
      breakdown: (() => {
        try {
          if (apiRes.data.graphdata) {
            let graphdata = apiRes.data.graphdata;
            if (typeof graphdata === 'string') {
              let cleanData = graphdata.replace(/```json\n?/g, '').replace(/```/g, '').trim();
              try {
                graphdata = JSON.parse(cleanData);
              } catch {
                cleanData = cleanData.replace(/^\s*{\s*/, '{').replace(/\s*}\s*$/, '}');
                graphdata = JSON.parse(cleanData);
              }
            }
            return Object.entries(graphdata)
              .filter(([key]) => key !== 'overall_greenwashing_score')
              .map(([key, value]: [string, any]) => ({
                type: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                value: Math.round((value?.score ?? 0) * 10)
              }));
          }
          return (apiRes.data.breakdown ?? []).map((d: any) => ({
            type: d.type,
            value: Math.round(d.value ?? 0)
          }));
        } catch (e) {
          console.error('Failed to parse breakdown data:', e);
          return [];
        }
      })(),
      evidenceGroups: (() => {
        const sec2 = extractSection(apiRes.data.final_synthesis ?? "", 2);
        return sec2
          ? [{
              type: "Key Findings and Evidence from Document Analysis",
              items: [{ quote: sec2.trim(), why: "" }]
            }]
          : [];
      })(),
      external: (() => {
        const sec4 = extractSection(apiRes.data.final_synthesis ?? "", 4);
        return sec4 ? [sec4.trim()] : [];
      })(),
      recommendedSteps: (() => {
        const sec5 = extractSection(apiRes.data.final_synthesis ?? "", 5);
        return sec5 ? sec5.trim() : "";
      })(),
    }
  : viewLS ?? { ...mockData, evidenceGroups: null };

  console.log('Processed view data:', view);
  console.log("Final synthesis raw:", view.final_synthesis);
  console.log('Score:', view.score);
  console.log('Breakdown:', view.breakdown);
  console.log('Evidence groups:', view.evidenceGroups);
  console.log('External:', view.external);

  const reportSections = parseFinalSynthesis(view.final_synthesis);

const safeBreakdown = Array.isArray(view?.breakdown)
  ? view.breakdown.filter(
      (d: any) => d && typeof d.value === 'number' && !Number.isNaN(d.value)
    )
  : [];

return (
  <div className="min-h-screen [background-image:var(--gradient-soft)]">
    <Seo
      title={`${view.name} | ${t('company.title')}`}
      description={`${t('dashboard.riskScore')} ${view.score}, ${view.summary}`}
      canonical={typeof window !== 'undefined' ? window.location.href : undefined}
    />
    <TopNav />
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">{t('company.title')}</h1>
        <p className="text-muted-foreground mt-1">{t('company.subtitle')}</p>
      </header>

      {/* Risk & Breakdown */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>{t('company.overallRisk')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="relative">
                <div className="h-28 w-28 rounded-full grid place-items-center border-2"
                     style={{ borderColor: "hsl(var(--accent))", boxShadow: "var(--shadow-glow)" }}>
                  <span className="text-3xl font-bold">{view.score}</span>
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">{t('company.riskLevel')}</span>
                  <Badge variant={riskTone(view.score) as any}>
                    {(() => {
                      if (view.score >= 70) return t('company.high');
                      if (view.score >= 40) return t('company.medium');
                      return t('company.low');
                    })()}
                  </Badge>
                </div>
                <div className="mt-2 leading-relaxed">
                  {view.summary ? <p>{view.summary}</p> : <p className="text-muted-foreground">No summary available</p>}
                </div>
                <div className="mt-3 flex gap-2">
                  <Button asChild><a href="#evidence">{t('company.viewEvidence')}</a></Button>
                  <Button variant="secondary" asChild><a href="#actions">{t('company.nextSteps')}</a></Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>1.Risk Type Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            {safeBreakdown.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={safeBreakdown} outerRadius={80}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="type" />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} />
                  <Tooltip />
                  <Radar
                    name="Risk"
                    dataKey="value"
                    stroke="hsl(var(--accent))"
                    fill="hsl(var(--accent))"
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full grid place-items-center text-sm text-muted-foreground">
                No visualization data available (awaiting analysis or insufficient data)
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Evidence / External / Actions */}
      <section id="evidence" className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>2.Key Findings and Evidence from Document Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            {Array.isArray(view?.evidenceGroups) && view.evidenceGroups.length > 0 ? (
              <div className="whitespace-pre-line">{view.evidenceGroups[0].items[0].quote}</div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <p>No report content available</p>
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>3.Specific Recommendations for Stakeholders</CardTitle>
            </CardHeader>
            <CardContent>
              {Array.isArray(view?.external) && view.external.length > 0 ? (
                <div className="whitespace-pre-line">{view.external[0]}</div>
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  <p>No report content available</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card id="actions">
            <CardHeader>
              <CardTitle>4.Risk Assessment and Concerns</CardTitle>
            </CardHeader>
            <CardContent>
              {view.recommendedSteps ? (
                <div className="whitespace-pre-line">{view.recommendedSteps}</div>
              ) : (
                <p>No recommendations available</p>
              )}
              <div className="mt-4 flex gap-2">
                <Button asChild><Link to="/upload">{t('company.addReports')}</Link></Button>
                <Button variant="secondary">{t('company.exportPdf')}</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
    <FloatingChatbot />
  </div>
);

}
export default Company;
