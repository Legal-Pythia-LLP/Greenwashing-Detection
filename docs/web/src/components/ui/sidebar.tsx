'use client';

import {cn} from '@lp/utils/css';
import {X} from 'lucide-react';
import {Component} from './piechart';
import {ComponentRadar} from './radarchart';

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
  message: string;
}

interface ScoreData {
  Metric: string;
  Score: number;
}

interface AnalysisResult {
  metrics: ScoreData[];
  overallScore: number | null; // Single overall score
}

function ExtractScore(message: string): AnalysisResult {
  const result: AnalysisResult = {
    metrics: [],
    overallScore: null,
  };

  if (!message?.trim()) return result;

  // Extract overall score (as number)
  const overallScoreMatch = message.match(
    /\**Overall Greenwashing Score\**:\s*((?:\d*\.\d+)|(?:\d+))/i
  );
  if (overallScoreMatch) {
    result.overallScore = parseFloat(overallScoreMatch[1]);
  }

  // Extract metrics table if it exists
  if (message.includes('|--')) {
    try {
      const rows = message.match(/\|.*?\|.*?\|/g)?.slice(2) || [];
      for (const row of rows) {
        const cols = row
          .split(/\s*\|\s*/)
          .map((x) => x.trim())
          .filter((x) => x);
        if (cols.length >= 2 && !isNaN(Number(cols[1]))) {
          result.metrics.push({
            Metric: cols[0],
            Score: Number(cols[1]),
          });
        }
      }
    } catch (error) {
      console.error(error);
    }
  }

  return result;
}

export const Sidebar = ({isOpen, onClose, onOpen, message}: SidebarProps) => {
  const r = ExtractScore(message);
  const score = r.overallScore ?? 0;
  const data: RadarChartData[] = transformToSimpleFormat(r.metrics);

  return (
    <>
      <div
        className={cn(
          'flex flex-col fixed inset-0 left-0 z-50 w-[34rem] px-8 transition-transform border-gray-300/50',
          'translate-x-0',
          'transition',
          'overflow-auto',
          'h-full',
          isOpen ? 'bg-white border-r-2' : 'border-r-0 bg-transparent'
        )}>
        <div className='flex flex-col h-full justify-between py-4'>
          <div className='flex items-center justify-end'>
            {isOpen ? (
              <button
                onClick={() => {
                  onClose();
                }}
                className='fixed top-4 left-4 z-40 p-2 text-white bg-blue-500 rounded-md hover:bg-blue-600'>
                <X className='h-6 w-6' />
              </button>
            ) : (
              <button
                onClick={() => {
                  onOpen();
                }}
                className='fixed top-4 left-4 z-40 p-2 text-white bg-blue-500 rounded-md hover:bg-blue-600'>
                <svg
                  xmlns='http://www.w3.org/2000/svg'
                  viewBox='0 0 24 24'
                  fill='currentColor'
                  className='h-6 w-6'>
                  <path d='M3 3v18h18' stroke='currentColor' strokeWidth='2' fill='none' />
                  <circle cx='6' cy='12' r='1.5' fill='currentColor' />
                  <circle cx='10' cy='8' r='1.5' fill='currentColor' />
                  <circle cx='14' cy='14' r='1.5' fill='currentColor' />
                  <circle cx='18' cy='6' r='1.5' fill='currentColor' />
                  <path
                    d='M6 12L10 8L14 14L18 6'
                    stroke='currentColor'
                    strokeWidth='2'
                    fill='none'
                  />
                </svg>
              </button>
            )}
          </div>

          {isOpen && (
            <>
              <Component score={score} />
              <ComponentRadar data={data} />
            </>
          )}
        </div>
      </div>
    </>
  );
};
