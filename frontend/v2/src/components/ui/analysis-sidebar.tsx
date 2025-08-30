'use client';

import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Component as ComponentPie } from '@/components/ui/piechart';
import { ComponentRadar } from '@/components/ui/radarchart';

interface RadarChartData {
  name: string;
  value: number;
}

function transformToSimpleFormat(scores: ScoreData[]): RadarChartData[] {
  return scores.map((score) => ({
    name: score.Metric,
    value: score.Score,
  }));
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onOpen: () => void;
  message: any; // Supports object or string
}

interface ScoreData {
  Metric: string;
  Score: number;
}

interface AnalysisResult {
  metrics: ScoreData[];
  overallScore: number | null; // Single overall score
}

function ExtractScore(message: any): AnalysisResult {
  const result: AnalysisResult = {
    metrics: [],
    overallScore: null,
  };

  if (!message) return result;

  if (typeof message === 'object') {
    try {
      for (const [metric, value] of Object.entries(message)) {
        if (metric === 'overall_greenwashing_score') {
          result.overallScore = (value as any).score ?? null;
        } else if (value && typeof value === 'object' && 'score' in (value as any)) {
          result.metrics.push({ Metric: metric, Score: (value as any).score });
        }
      }
      return result;
    } catch (err) {
      console.error('Error parsing JSON metrics:', err);
    }
  }

  if (typeof message === 'string') {
    try {
      const parsed = JSON.parse(message);
      return ExtractScore(parsed);
    } catch {}

    const overallScoreMatch = message.match(/\**Overall Greenwashing Score\**:\s*((?:\d*\.\d+)|(?:\d+))/i);
    if (overallScoreMatch) {
      result.overallScore = parseFloat(overallScoreMatch[1]);
    }

    if (message.includes('|--')) {
      try {
        const rows = message.match(/\|.*?\|.*?\|/g)?.slice(2) || [];
        for (const row of rows) {
          const cols = row
            .split(/\s*\|\s*/)
            .map((x) => x.trim())
            .filter((x) => x);
          if (cols.length >= 2 && !isNaN(Number(cols[1]))) {
            result.metrics.push({ Metric: cols[0], Score: Number(cols[1]) });
          }
        }
      } catch (error) {
        console.error(error);
      }
    }
  }

  return result;
}

export const Sidebar = ({ isOpen, onClose, onOpen, message }: SidebarProps) => {
  const r = ExtractScore(message);
  const score = r.overallScore ?? 0;
  const data: RadarChartData[] = transformToSimpleFormat(r.metrics);

  return (
    <>
      <div
        className={cn(
          'fixed left-0 top-0 z-40 h-full w-[22rem] md:w-[28rem] pt-14 md:pt-16 px-4 transition-transform duration-300',
          isOpen ? 'translate-x-0 bg-background border-r' : '-translate-x-full pointer-events-none'
        )}
      >
        <div className='flex flex-col h-full justify-between py-4'>
          <div className='flex items-center justify-between mb-3'>
            <h3 className='text-sm font-medium text-muted-foreground'>Analysis Panel</h3>
            <Button variant='ghost' size='icon' onClick={onClose} aria-label='Close'>
              <X className='h-4 w-4' />
            </Button>
          </div>

          {isOpen && (
            <>
              <ComponentPie score={score} />
              <ComponentRadar data={data} />
            </>
          )}
        </div>
      </div>
    </>
  );
};
