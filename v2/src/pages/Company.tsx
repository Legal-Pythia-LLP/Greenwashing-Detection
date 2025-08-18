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
import i18next from "i18next";


/**
 * Extracts the specified section from final_synthesis
 * @param text Full final_synthesis text
 * @param sectionNumber Section number to extract (2, 4, 5)
 * @returns Corresponding section content as a string (without the title)
 */
function extractSection(text: string, sectionNumber: number): string {
  if (!text || typeof text !== "string") return "";

  const regex = new RegExp(
    `(?:^|\\n)${sectionNumber}\\.\\s[^\\n]*\\n([\\s\\S]*?)(?=\\n{2,}${sectionNumber + 1}\\.\\s|$)`,
    "i"
  );

  const match = text.match(regex);
  if (match) {
    return match[1].trim();
  }
  return "";
}

function highlightGreenwashing(text: string) {
  if (!text) return "";
  const keywords = [
    // ==== English buzzwords ====
    "climate", "carbon", "emissions?", "footprint", "neutrality",
    "low[- ]?carbon","high[- ]?carbon", "carbon[- ]?neutral", "net[- ]?zero", "climate[- ]?neutral",
    "climate[- ]?positive", "offsets?", "carbon credits?", "sustainable",
    "responsible", "green", "eco[- ]?friendly", "renewable", "environmentally[- ]?friendly",
    "aligned with science", "ambitious goals?", "science[- ]?based targets?",

    // ==== German buzzwords ====
    "klima", "kohlenstoff", "emission(en)?", "fußabdruck", "neutralität",
    "niedrig[- ]?kohlenstoff", "CO2[- ]?neutral", "klimaneutral", "klimapositiv",
    "kompensationen?", "CO2[- ]?gutschriften?", "nachhaltig", "verantwortungsvoll",
    "grün", "umweltfreundlich", "erneuerbar", "wissenschafts[- ]?basierte Ziele?",

    // ==== Italian buzzwords ====
    "clima", "carbonio", "emissioni?", "impronta", "neutralità",
    "basso[- ]?carbonio", "carbon[- ]?neutral[e]?", "neutro rispetto al clima", 
    "clima positivo", "compensazioni?", "crediti di carbonio?", "sostenibile",
    "responsabile", "verde", "eco[- ]?compatibile", "rinnovabile",
    "obiettivi basati sulla scienza", "ambiziosi obiettivi?"
  ];


  const regex = new RegExp(`(${keywords.join("|")})`, "gi");
  return text.replace(
    regex,
    `<span style="color:green; font-weight:bold;">$1</span>`
  );
}



function formatBullets(text?: string): string {
  if (!text) return "";
  return text
    .replace(/^\*\s*/gm, "")
    .replace(
      /^([A-Za-z\/ ,&'-]{1,80}):/gm,
      (match, p1) => {
        if (p1.length > 60) return match; 
        return `<strong>${p1}:</strong>`;
      }
    );
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
  const { t, i18n } = useTranslation();
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

const rawLang = i18n.language || "en";
const langMap: Record<string, string> = {
  en: "en", "en-US": "en", "en-GB": "en",
  de: "de", "de-DE": "de",
  it: "it", "it-IT": "it",
 };
const preferred = langMap[rawLang] || rawLang.slice(0, 2) || "en";
const fsI18n = (apiRes?.data as any)?.final_synthesis_i18n || null;
const pickFinal =
   (fsI18n && (fsI18n[preferred] || fsI18n["de"] || fsI18n["it"] || fsI18n["zh"] || fsI18n["es"])) ||
   (apiRes?.data as any)?.final_synthesis ||
   (apiRes?.data as any)?.response ||
   "";

function extractSectionOneBody(text: string): string {
  if (!text) return "";
  const re = /(?:^|\n)\s*(?:\*\*)?\s*1\.\s+[^\n]*(?:\*\*)?\s*\n([\s\S]*?)(?=\n\s*(?:\*\*)?\s*2\.\s+|$)/i;
  const m = text.match(re);
  return m ? m[1].trim() : "";
}

function sanitizeSynthesis(text: string): string {
  if (!text) return "";
  const prefaces = [
    /^okay,\s*here'?s\s+the\s+.*?translation.*?$/i,
    /^hier\s+ist\s+die\s+deutsche\s+übersetzung.*?$/i,
    /^ecco\s+la\s+traduzione.*?$/i
  ];
  const firstHeading = text.search(/^##\s+|^\s*\d+\.\s+/gmi);
  if (firstHeading === -1) return text;
  const head = text
    .slice(0, firstHeading)
    .split("\n")
    .filter((line) => !prefaces.some((re) => re.test(line.trim())))
    .join("\n");
  const tail = text.slice(firstHeading);
  return ((head.trim() ? `${head}\n` : "") + tail).trim();
}


  
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
const cleanedFinal = sanitizeSynthesis(pickFinal);
const view = apiRes?.data
  ? {
      name: apiRes.data.company_name,


      final_synthesis: pickFinal,

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
          const body = extractSectionOneBody(cleanedFinal);
          if (body) return body;
          const firstPara = cleanedFinal.split(/\n{2,}/)[0]?.trim() || "";
          return firstPara || cleanedFinal.slice(0, 200);
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

            const lang = (i18next.language || "en").slice(0, 2);

            return Object.entries(graphdata)
              .filter(([key]) => key !== 'overall_greenwashing_score')
              .map(([key, value]: [string, any]) => {
                const score = Math.round((value?.score ?? 0) * 10);
                const type_i18n = value?.type_i18n ?? null;

                return {
                  type: type_i18n?.[lang] ?? key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                  value: score
                };
              });
          }

          return (apiRes.data.breakdown ?? []).map((d: any) => {
            const lang = (i18next.language || "en").slice(0, 2);
            return {
              type: d.type_i18n?.[lang] ?? d.type,
              value: Math.round(d.value ?? 0)
            };
          });
        } catch (e) {
          console.error('Failed to parse breakdown data:', e);
          return [];
        }
      })(),
      evidenceGroups: (() => {
        const sec2 = extractSection(pickFinal ?? "", 2);
        return sec2
          ? [{
              type: "Key Findings and Evidence from Document Analysis",
              items: [{ quote: sec2.trim(), why: "" }]
            }]
          : [];
      })(),
      external: (() => {
        const sec4 = extractSection(pickFinal ?? "", 4);
        return sec4 ? [sec4.trim()] : [];
      })(),
      riskAssessment: (() => {
        const sec5 = extractSection(pickFinal ?? "", 5);
        return sec5 ? [sec5.trim()] : [];
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
              <CardTitle>1. {t('company.riskBreakdown')}</CardTitle>
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
            <CardTitle>2. {t('company.keyFindings')}</CardTitle>
          </CardHeader>
            <CardContent>
              {Array.isArray(view?.evidenceGroups) && view.evidenceGroups.length > 0 ? (
                (() => {
                  const raw = view.evidenceGroups[0].items[0].quote;

                    const TOKENS = {
                      quotation: ["Quotation", "Citazione", "Zitat"],
                      explanation: ["Explanation", "Spiegazione", "Erläuterung"],
                      revisedExplanation: ["Revised Explanation", "Spiegazione Riveduta", "Revidierte Erläuterung"],
                      score: [
                        "Greenwashing Likelihood Score",
                        "Punteggio di Probabilità di Greenwashing",
                        "Greenwashing-Wahrscheinlichkeitswert",
                      ],
                      revisedScore: ["Revised Score", "Punteggio Riveduto", "Revidierter Score"],
                      externalVerification: [
                        "External Verification Conducted and Verification Results",
                        "Verifica Esterna Eseguita e Risultati della Verifica",
                        "Durchgeführte externe Verifizierung und Verifizierungsergebnisse",
                      ],
                      furtherVerification: [
                        "Further Verification Required",
                        "Ulteriore Verifica Richiesta",
                        "Weiterer Verifizierungsbedarf",
                      ],
                    };

                    const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

                    const QUOTATION_RE = new RegExp(
                      `(?:^|\\n)(${TOKENS.quotation.map(esc).join("|")})\\s*:`,
                      "i"
                    );

                    function formatEvidenceDetailsLocalized(text?: string): string {
                      if (!text) return "";
                      const heads = [
                        ...TOKENS.explanation,
                        ...TOKENS.revisedExplanation,
                        ...TOKENS.score,
                        ...TOKENS.revisedScore,
                        ...TOKENS.externalVerification,
                        ...TOKENS.furtherVerification,
                      ].map(esc);

                      const headRegex = new RegExp(`^(${heads.join("|")})\\s*:`, "gmi");

                    
                      return text
                        .replace(headRegex, "<strong>$1:</strong>")
                        .replace(/^\*\s*(News Validation|Wikirate Validation|Validazione delle Notizie|Validazione Wikirate|Nachrichtenvalidierung|Wikirate-Validierung):/gmi, "* <strong>$1:</strong>");
                    }

                    const cleaned = raw.replace(/\b2\.\d+\s+/g, "");

                    const firstQIndex = cleaned.search(QUOTATION_RE);
                    const summary = firstQIndex > -1 ? cleaned.slice(0, firstQIndex).trim() : cleaned.trim();
                    const rest = firstQIndex > -1 ? cleaned.slice(firstQIndex) : "";

                    type Entry = { start: number; label: string; matchLen: number };
                    const entries: Entry[] = [];
                    if (rest) {
                      const reGlobal = new RegExp(QUOTATION_RE.source, "gi");
                      let m: RegExpExecArray | null;
                      while ((m = reGlobal.exec(rest)) !== null) {
                        entries.push({ start: m.index, label: m[1], matchLen: m[0].length });
                      }
                    }

                    const blocks = entries.map((e, i) => {
                      const start = e.start + e.matchLen;
                      const end = i + 1 < entries.length ? entries[i + 1].start : rest.length;
                      return { label: e.label, text: rest.slice(start, end).trim() };
                    });

                    return (
                      <div className="space-y-6">
                        {summary && <div className="whitespace-pre-line mt-2">{summary}</div>}

                        {blocks.map((block, idx) => {
                          const qIndex = idx + 1;
                          if (!block.text) return null;

                          const [firstLine, ...restLines] = block.text.split("\n").map((l) => l.trim());

                          return (
                            <div key={`q-${qIndex}`}>
                              <h4 className="font-semibold">{`2.${qIndex} ${block.label}`}</h4>

                              {firstLine && (
                                <blockquote
                                  className="italic text-muted-foreground mt-1"
                                  dangerouslySetInnerHTML={{
                                    __html: highlightGreenwashing(firstLine.replace(/^["']?|["']?$/g, "")),
                                  }}
                                />
                              )}


                              {restLines.length > 0 && (
                                <div
                                  className="whitespace-pre-line mt-2"
                                  dangerouslySetInnerHTML={{
                                    __html: formatEvidenceDetailsLocalized(restLines.join("\n")).replace(/\n/g, "<br/>"),
                                  }}
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()
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
            <CardTitle>3. {t('company.recommendations')}</CardTitle>
          </CardHeader>
          <CardContent>
            {Array.isArray(view?.external) && view.external.length > 0 ? (
              <div
                className="whitespace-pre-line"
                dangerouslySetInnerHTML={{
                  __html: formatBullets(view.external[0]).replace(/\n/g, "<br/>")
                }}
              />
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <p>No report content available</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>4. {t('company.riskAssessmentConcerns')}</CardTitle>
          </CardHeader>
          <CardContent>
            {Array.isArray(view?.riskAssessment) && view.riskAssessment.length > 0 ? (
              <div
                className="whitespace-pre-line"
                dangerouslySetInnerHTML={{
                  __html: formatBullets(view.riskAssessment[0]).replace(/\n/g, "<br/>")
                }}
              />
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <p>No report content available</p>
              </div>
            )}
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
