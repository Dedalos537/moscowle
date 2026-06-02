import type { ChartConfiguration, ChartData } from 'chart.js';

export const chartTooltip = {
  backgroundColor: 'rgba(26, 28, 22, 0.92)',
  titleFont: { family: 'Manrope', size: 12, weight: 700 },
  bodyFont: { family: 'Manrope', size: 13, weight: 600 },
  padding: { x: 14, y: 10 },
  cornerRadius: 10,
};

export const chartTooltipSoles = {
  ...chartTooltip,
  callbacks: { label: (ctx: any) => `S/ ${Number(ctx.raw).toLocaleString('es-PE', { minimumFractionDigits: 2 })}` },
};

export const chartLegendBottom = {
  position: 'bottom' as const,
  labels: { font: { family: 'Manrope', size: 11, weight: 600 }, padding: 12, usePointStyle: true, pointStyle: 'circle' as const },
};

export const xGridNone = { display: false };
export const yGridLight = { color: 'rgba(217, 219, 206, 0.4)' };

export const tickSmall = { font: { family: 'Manrope', size: 10, weight: 500 }, color: '#76796c' };
export const tickSmallBold = { font: { family: 'Manrope', size: 11, weight: 600 }, color: '#1a1c16' };

export const lineElements = { line: { tension: 0.4, borderWidth: 3 }, point: { radius: 4, hoverRadius: 6 } };

export const chartColors = ['#75a83a', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#ba1a1a'];

export function makeDoughnutOpts(): ChartConfiguration<'doughnut'>['options'] {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: chartLegendBottom, tooltip: chartTooltip },
    cutout: '68%',
  };
}

export function makeBarOpts(indexAxis: 'x' | 'y' = 'x'): ChartConfiguration<'bar'>['options'] {
  return {
    responsive: true,
    maintainAspectRatio: false,
    ...(indexAxis === 'y' ? { indexAxis: 'y' as const } : {}),
    plugins: {
      legend: { display: false },
      tooltip: chartTooltipSoles,
    },
    scales: {
      x: indexAxis === 'y'
        ? { grid: yGridLight, ticks: { ...tickSmall, color: '#76796c', callback: (val: any) => `S/${val}` }, beginAtZero: true }
        : { grid: xGridNone, ticks: tickSmall },
      y: indexAxis === 'y'
        ? { grid: { display: false }, ticks: tickSmallBold }
        : { grid: yGridLight, ticks: { ...tickSmall, color: '#76796c' }, beginAtZero: true },
    },
  };
}

export function makeLineOpts(): ChartConfiguration<'line'>['options'] {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: chartTooltipSoles },
    scales: {
      x: { grid: xGridNone, ticks: tickSmall },
      y: { grid: yGridLight, ticks: { ...tickSmall, color: '#76796c', callback: (val: any) => `S/${val}` }, beginAtZero: true },
    },
    elements: lineElements,
  };
}

export function makePieOpts(): ChartConfiguration<'pie'>['options'] {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: chartLegendBottom, tooltip: chartTooltipSoles },
  };
}
