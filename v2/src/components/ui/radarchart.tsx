"use client";

import { TrendingUp } from "lucide-react";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart } from "recharts";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";

interface RadarChartData {
  name: string;
  value: number;
}

const chartConfig = {
  desktop: {
    label: "Desktop",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig;

export function ComponentRadar({ data }: { data: RadarChartData[] }) {
  return (
    <Card>
      <CardHeader className="items-center">
        <CardTitle>Greenwashing Metic Profile</CardTitle>
        <CardDescription>Performance across key sustainability metrics (%)</CardDescription>
      </CardHeader>
      <CardContent className="pb-0">
        <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[30vh]">
          <RadarChart data={data}>
            <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
            <PolarAngleAxis dataKey="name" />
            <PolarGrid />
            <Radar dataKey="value" fill="var(--color-desktop)" fillOpacity={0.6} dot={{ r: 4, fillOpacity: 1 }} />
          </RadarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
