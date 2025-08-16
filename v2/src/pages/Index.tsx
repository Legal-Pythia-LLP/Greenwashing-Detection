import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import TopNav from "@/components/TopNav";
import Seo from "@/components/Seo";
import { FloatingChatbot } from "@/components/FloatingChatbot";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { TrendingUp, AlertTriangle, FileText } from "lucide-react";
import { useTranslation } from "react-i18next";
import { APIService } from "@/services/api.service";

interface Stats {
  high_risk_companies: number;
  pending_reports: number;
  high_priority_reports: number;
}

interface Company {
  id: string;
  name: string;
  score: number;
  type: string;
  date: string;
}

const trendData = [
  { date: "05-01", risks: 5 },
  { date: "05-08", risks: 7 },
  { date: "05-15", risks: 6 },
  { date: "05-22", risks: 9 },
  { date: "05-29", risks: 12 },
  { date: "06-05", risks: 15 },
];

const riskColor = (score: number) => (score >= 80 ? "destructive" : "secondary");

const Index = () => {
  const { t } = useTranslation();

  const [stats, setStats] = useState<Stats | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const data = await APIService.getDashboardData();

        if (data) {
          setStats(data.stats ?? {
            high_risk_companies: 128,
            pending_reports: 34,
            high_priority_reports: 9,
          });

          const sortedCompanies = Array.isArray(data.companies) 
            ? [...data.companies].sort((a, b) => b.score - a.score) 
            : [];
          setCompanies(sortedCompanies);
        } else {
          setStats(null);
          setCompanies([]);
        }
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
        setStats(null);
        setCompanies([]);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="min-h-screen [background-image:var(--gradient-soft)]">
      <Seo
        title={`${t('dashboard.title')} | ESG Decision & Compliance Support`}
        description={t('dashboard.subtitle')}
        canonical={typeof window !== 'undefined' ? window.location.href : undefined}
        jsonLd={{
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: t('nav.title'),
          applicationCategory: "BusinessApplication",
          description: t('dashboard.subtitle')
        }}
      />
      <TopNav />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <header className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            {t('dashboard.title')}
          </h1>
          <p className="text-muted-foreground mt-3 text-lg">{t('dashboard.subtitle')}</p>
        </header>

        <section aria-labelledby="metrics" className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {/* High Risk Companies */}
          <Card className="hover:shadow-xl transition-all duration-300 border-0 [box-shadow:var(--shadow-elevated)]">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                {t('dashboard.highRiskCompanies')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-destructive mb-1">
                {stats?.high_risk_companies ?? 0}
              </div>
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <TrendingUp className="h-3 w-3" />
                {t('dashboard.newInLast7Days')} 15
              </div>
            </CardContent>
          </Card>

          {/* Pending Reports */}
          <Card className="hover:shadow-xl transition-all duration-300 border-0 [box-shadow:var(--shadow-elevated)]">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-primary" />
                {t('dashboard.pendingReports')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold text-primary mb-1">
                {stats?.pending_reports ?? 0}
              </div>
              <div className="text-sm text-muted-foreground">
                {t('dashboard.highPriority')}{" "}
                <span className="font-semibold text-accent">
                  {stats?.high_priority_reports ?? 0}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Risk Trend */}
          <Card className="hover:shadow-xl transition-all duration-300 border-0 [box-shadow:var(--shadow-elevated)]">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">{t('dashboard.riskTrend')}</CardTitle>
            </CardHeader>
            <CardContent className="h-32">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" hide />
                  <YAxis hide />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--card))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '8px'
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="risks"
                    stroke="hsl(var(--primary))"
                    strokeWidth={3}
                    dot={{ fill: 'hsl(var(--accent))', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </section>

        {/* Company Ranking Table */}
        <section aria-labelledby="ranking">
          <div className="flex items-center justify-between mb-6">
            <h2 id="ranking" className="text-2xl font-semibold">{t('dashboard.companyRanking')}</h2>
            <Button asChild className="shadow-lg">
              <Link to="/upload" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                {t('dashboard.uploadNewReport')}
              </Link>
            </Button>
          </div>

          <Card className="border-0 [box-shadow:var(--shadow-elevated)]">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent border-b-2 border-border">
                    <TableHead className="font-semibold">{t('dashboard.companyName')}</TableHead>
                    <TableHead className="font-semibold">{t('dashboard.riskScore')}</TableHead>
                    <TableHead className="font-semibold">{t('dashboard.mainType')}</TableHead>
                    <TableHead className="font-semibold">{t('dashboard.analysisDate')}</TableHead>
                    <TableHead className="text-right font-semibold">{t('dashboard.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8">
                        {t('dashboard.loading')}
                      </TableCell>
                    </TableRow>
                  ) : companies.length > 0 ? (
                    companies.map((c) => (
                      <TableRow key={c.id} className="hover:bg-muted/50 transition-colors">
                        <TableCell className="font-medium py-4">{c.name}</TableCell>
                        <TableCell>
                          <Badge
                            variant={riskColor(c.score) as any}
                            className="px-3 py-1 text-sm font-semibold"
                          >
                            {c.score}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {t(`greenwashingTypes.${c.type}`) ?? c.type}
                        </TableCell>
                        <TableCell className="text-muted-foreground">{c.date}</TableCell>
                        <TableCell className="text-right">
                          <Button variant="secondary" asChild className="hover:shadow-md">
                            <Link to={`/company/${c.id}`} aria-label={t('dashboard.viewAnalysis', { company: c.name })}>
                              {t('dashboard.viewDetails')}
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                        {t('dashboard.noData')}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>
      </main>

      <FloatingChatbot />
    </div>
  );
};

export default Index;
