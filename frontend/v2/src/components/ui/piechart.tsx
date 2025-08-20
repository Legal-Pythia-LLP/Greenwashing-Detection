"use client";

import { TrendingUp } from "lucide-react";
import { TrendingDown } from "lucide-react";
import { Label, PolarGrid, PolarRadiusAxis, RadialBar, RadialBarChart } from "recharts";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ChartConfig, ChartContainer } from "@/components/ui/chart";

interface ChartData {
  score: number;
  fill: string;
}

function Calculate(score: number) {
  return (score / 10) * 360;
}

const chartConfig = {
  safari: {
    label: "Safari",
    color: "hsl(var(--chart-2))",
  },
} satisfies ChartConfig;

export function Component({ score }: { score: number }) {
  const chartData: ChartData[] = score !== null ? [{ score, fill: "var(--color-safari)" }] : [];
  let message = "";
  if (score < 5) {
    message = "Low likelihood of greenwashing";
  } else if (score >= 5 && score <= 7) {
    message = "Moderate likelihood of greenwashing";
  } else if (score > 7 && score <= 10) {
    message = "High likelihood of greenwashing, need further investigation";
  }

  return (
    <Card className="flex flex-col">
      <CardHeader className="items-center pb-0">
        <CardTitle>Greenwashing Score</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 pb-0">
        <ChartContainer config={chartConfig} className="mx-auto aspect-square max-h-[30vh]">
          <RadialBarChart data={chartData} startAngle={0} endAngle={Calculate(score)} innerRadius={80} outerRadius={110}>
            <PolarGrid gridType="circle" radialLines={false} stroke="none" className="first:fill-muted last:fill-background" polarRadius={[86, 74]} />
            <RadialBar dataKey="score" background cornerRadius={10} />
            <PolarRadiusAxis tick={false} tickLine={false} axisLine={false}>
              <Label
                content={({ viewBox }) => {
                  if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                    return (
                      <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle" dominantBaseline="middle">
                        <tspan x={viewBox.cx} y={viewBox.cy} className="fill-foreground text-4xl font-bold">
                          {score * 10}%
                        </tspan>
                        <tspan x={viewBox.cx} y={(viewBox.cy || 0) + 24} className="fill-muted-foreground"></tspan>
                      </text>
                    );
                  }
                }}
              />
            </PolarRadiusAxis>
          </RadialBarChart>
        </ChartContainer>
      </CardContent>
      <CardFooter className="flex-col gap-2 text-sm">
        <div className="flex items-center gap-2 font-medium leading-none">
          {message} <TrendingUp className="h-4 w-4" />
        </div>
      </CardFooter>
    </Card>
  );
}
