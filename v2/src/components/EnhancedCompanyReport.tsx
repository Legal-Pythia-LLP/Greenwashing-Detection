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
              执行摘要
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
              下载完整报告
            </Button>
            <Button variant="outline">上传更多文档</Button>
          </div>
        </CardContent>
      </Card>

      {/* Key Findings and Evidence */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            关键发现与证据链
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {company.evidenceGroups?.map((group, groupIdx) => (
            <div key={groupIdx} className="space-y-4">
              <h4 className="font-semibold text-primary border-b pb-2">{group.type}</h4>
              {group.items.map((item, itemIdx) => (
                <div key={itemIdx} className="border rounded-lg p-4 space-y-3">
                  <div className="bg-muted p-3 rounded border-l-4 border-l-accent">
                    <p className="font-medium mb-1">原文引用:</p>
                    <p className="italic">"{item.quote}"</p>
                  </div>
                  
                  <div>
                    <p className="font-medium mb-1">分析说明:</p>
                    <p className="text-muted-foreground">{item.why}</p>
                  </div>

                  {item.score && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium">漂绿可能性评分:</span>
                      <Badge variant={item.score >= 70 ? "destructive" : "secondary"}>
                        {item.score}/100
                      </Badge>
                    </div>
                  )}

                  {item.verification && (
                    <Alert>
                      <CheckCircle className="h-4 w-4" />
                      <AlertDescription>
                        <strong>外部验证结果:</strong> {item.verification}
                      </AlertDescription>
                    </Alert>
                  )}

                  {item.further_verification && (
                    <Alert>
                      <ExternalLink className="h-4 w-4" />
                      <AlertDescription>
                        <strong>需进一步验证:</strong> {item.further_verification}
                      </AlertDescription>
                    </Alert>
                  )}
                </div>
              ))}
            </div>
          )) || (
            <p className="text-muted-foreground">暂无详细证据链数据</p>
          )}
        </CardContent>
      </Card>

      {/* Greenwashing Types & Overall Score */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>漂绿类型评估</CardTitle>
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
            <CardTitle>风险雷达图</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="type" className="text-xs" />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tickCount={5} className="text-xs" />
                  <Radar
                    name="风险评分"
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
          <CardTitle>利益相关者建议</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">投资者</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• 要求公司提供更具体的量化目标</li>
                <li>• 关注第三方认证和验证报告</li>
                <li>• 建立ESG绩效监督机制</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">监管机构</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• 加强信息披露规范要求</li>
                <li>• 建立漂绿行为处罚机制</li>
                <li>• 推动行业标准化进程</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">企业管理层</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• 建立透明的ESG数据管理体系</li>
                <li>• 定期进行第三方审计</li>
                <li>• 避免使用模糊或误导性表述</li>
              </ul>
            </div>
            <div className="space-y-2">
              <h4 className="font-semibold text-primary">分析师</h4>
              <ul className="text-sm space-y-1 text-muted-foreground">
                <li>• 重点关注数据可验证性</li>
                <li>• 评估ESG目标的现实性</li>
                <li>• 跟踪长期绩效表现</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risk Assessment and External Information */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>风险评估与关注点</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Alert variant={riskLevel === "high" ? "destructive" : "default"}>
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  <strong>风险等级:</strong> {riskLevel === "high" ? "高风险" : riskLevel === "medium" ? "中等风险" : "低风险"}
                </AlertDescription>
              </Alert>
              <div className="text-sm space-y-2 text-muted-foreground">
                <p>• 缺乏具体量化指标可能导致投资者质疑</p>
                <p>• 模糊表述增加监管合规风险</p>
                <p>• 第三方验证不足影响公信力</p>
                <p>• 需要加强数据透明度和可追溯性</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>外部验证信息</CardTitle>
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
                <p className="text-muted-foreground text-sm">暂无外部验证信息</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}