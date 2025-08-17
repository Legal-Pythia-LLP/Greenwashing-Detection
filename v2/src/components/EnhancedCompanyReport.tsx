import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from "recharts";
import { Shield, AlertTriangle, FileText, CheckCircle, ExternalLink } from "lucide-react";

interface EvidenceItem {
  quote: string;
  why: string;
  score?: number;
  verification?: string;
  further_verification?: string;
}

interface EvidenceGroup {
  type: string;
  items: EvidenceItem[];
}

interface EnhancedCompanyReportProps {
  company: {
    name: string;
    score: number;
    summary: string;
    breakdown: Array<{ type: string; value: number }>;
    evidenceGroups: EvidenceGroup[] | null;
    external: string[];
  };
}

export function EnhancedCompanyReport({ company }: EnhancedCompanyReportProps) {
  const riskLevel = company.score >= 80 ? "high" : company.score >= 60 ? "medium" : "low";
  const riskBadgeVariant = riskLevel === "high" ? "destructive" : riskLevel === "medium" ? "accent" : "secondary";

  const radarData = company.breakdown?.map(item => ({
    type: item.type,
    value: item.value,
    fullMark: 100
  })) || [];

  return (
    <div className="space-y-8">
      {/* Executive Summary */}
      <Card className="border-l-4 border-l-primary">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Executive Summary
            </CardTitle>
            <Badge variant={riskBadgeVariant === "accent" ? "secondary" : riskBadgeVariant} className="text-lg px-3 py-1">
              {company.score}/100
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground leading-relaxed">{company.summary}</p>
          <div className="mt-4 flex gap-2">
            <Button>
              <FileText className="h-4 w-4 mr-2" />
              Download Full Report
            </Button>
            <Button variant="outline">Upload More Documents</Button>
          </div>
        </CardContent>
      </Card>

      {/* Key Findings and Evidence */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Key Findings & Evidence
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {company.evidenceGroups?.map((group, groupIdx) => (
            <div key={groupIdx} className="space-y-4">
              <h4 className="font-semibold text-primary border-b pb-2">{group.type}</h4>
              {group.items.map((item, itemIdx) => (
                <div key={itemIdx} className="border rounded-lg p-4 space-y-3">
                  <div className="bg-muted p-3 rounded border-l-4 border-l-accent">
                    <p className="font-medium mb-1">Original Quote:</p>
                    <p className="italic">"{item.quote}"</p>
                  </div>
                  
                  <div>
                    <p className="font-medium mb-1">Analysis:</p>
                    <p className="text-muted-foreground">{item.why}</p>
                  </div>

                  {item.score && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium">Greenwashing Likelihood Score:</span>
                      <Badge variant={item.score >= 70 ? "destructive" : "secondary"}>
                        {item.score}/100
                      </Badge>
                    </div>
                  )}

                  {item.verification && (
                    <Alert>
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>External Verification:</strong> {item.verification}
                      </AlertDescription>
                    </Alert>
                  )}

                  {item.further_verification && (
                    <Alert>
                      <ExternalLink className="h-4 w-4" />
                      <AlertDescription>
                        <strong>Further Verification Needed:</strong> {item.further_verification}
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              ))}
            </div>
          )) || (
            <p className="text-muted-foreground">No detailed evidence available</p>
          )}
        </CardContent>
      </Card>

      {/* Greenwashing Types & Overall Score */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Greenwashing Type Assessment</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {company.breakdown.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <span className="text-sm">{item.type}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-muted rounded-full h-2">
                      <div 
                        className="h-2 rounded-full bg-gradient-to-r from-primary to-accent"
                        style={{ width: `${item.value}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium w-8">{item.value}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk Radar Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="type" className="text-xs" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tickCount={5} className="text-xs" />
                  <Radar
                    name="Risk Score"
                    dataKey="value"
                    stroke="hsl(var(--primary))"
                    fill="hsl(var(--primary))"
                    fillOpacity={0.2}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stakeholder Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Stakeholder Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">Investors</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Request more specific quantitative targets from the company</li>
                <li>• Pay attention to third-party certifications and verification reports</li>
                <li>• Establish ESG performance monitoring mechanisms</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">Regulators</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Strengthen disclosure requirements</li>
                <li>• Establish penalties for greenwashing behavior</li>
                <li>• Promote industry standardization</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">Company Management</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Build a transparent ESG data management system</li>
                <li>• Conduct regular third-party audits</li>
                <li>• Avoid ambiguous or misleading statements</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">Analysts</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• Focus on data verifiability</li>
                <li>• Assess the realism of ESG targets</li>
                <li>• Track long-term performance</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Assessment and External Information */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Risk Assessment & Key Considerations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Alert variant={riskLevel === "high" ? "destructive" : "default"}>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <strong>Risk Level:</strong> {riskLevel === "high" ? "High" : riskLevel === "medium" ? "Medium" : "Low"}
                </AlertDescription>
              </Alert>
              <div className="text-sm space-y-2 text-muted-foreground">
                <p>• Lack of specific quantitative metrics may raise investor concerns</p>
                <p>• Ambiguous statements increase regulatory compliance risk</p>
                <p>• Insufficient third-party verification affects credibility</p>
                <p>• Need to enhance data transparency and traceability</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>External Verification Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {company.external.length > 0 ? (
                company.external.map((info, idx) => (
                  <div key={idx} className="p-3 bg-muted rounded border-l-4 border-l-accent">
                    <p className="text-sm">{info}</p>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground text-sm">No external verification information available</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}