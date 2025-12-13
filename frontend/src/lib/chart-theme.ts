/**
 * Centralized ECharts theme configuration for consistent styling across all charts.
 * Supports light/dark mode with glassmorphic tooltip styling.
 */

// Chart color palette - professional and muted for analytics
export const CHART_COLORS = {
  primary: 'hsl(215, 60%, 48%)',    // Deeper, professional blue
  success: 'hsl(145, 50%, 42%)',    // Muted green
  purple: 'hsl(265, 45%, 50%)',     // Subdued purple
  orange: 'hsl(25, 70%, 50%)',      // Muted orange
  cyan: 'hsl(195, 65%, 45%)',       // Softer cyan
  red: 'hsl(0, 55%, 50%)',          // Muted red
  yellow: 'hsl(45, 75%, 48%)',      // Softer yellow
  teal: 'hsl(173, 55%, 38%)',       // Muted teal
  pink: 'hsl(330, 55%, 52%)',       // Softer pink
  indigo: 'hsl(245, 48%, 48%)',     // Softer indigo
} as const;

// Color array for series
export const CHART_COLOR_PALETTE = [
  CHART_COLORS.primary,
  CHART_COLORS.success,
  CHART_COLORS.purple,
  CHART_COLORS.orange,
  CHART_COLORS.cyan,
  CHART_COLORS.red,
  CHART_COLORS.yellow,
  CHART_COLORS.teal,
  CHART_COLORS.pink,
  CHART_COLORS.indigo,
];

// Light theme configuration
export const lightTheme = {
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, system-ui, sans-serif',
    color: 'hsl(222.2, 47.4%, 11.2%)',
  },
  title: {
    textStyle: {
      fontWeight: 600,
      fontSize: 14,
      color: 'hsl(222.2, 84%, 4.9%)',
    },
    subtextStyle: {
      fontSize: 12,
      color: 'hsl(215.4, 16.3%, 46.9%)',
    },
  },
  legend: {
    textStyle: {
      color: 'hsl(215.4, 16.3%, 46.9%)',
      fontSize: 12,
    },
    itemGap: 16,
    itemWidth: 12,
    itemHeight: 12,
  },
  tooltip: {
    backgroundColor: 'hsl(0, 0%, 100%)',  // Solid white, no blur
    borderColor: 'rgba(0, 0, 0, 0.1)',
    borderWidth: 1,
    borderRadius: 6,  // Was 12 - more angular
    padding: [8, 12], // Tighter padding
    textStyle: {
      color: 'hsl(220, 15%, 16%)',
      fontSize: 12,
    },
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08);',  // Removed backdrop-filter
  },
  axisPointer: {
    lineStyle: {
      color: 'hsl(221.2, 83.2%, 53.3%)',
      type: 'dashed',
      opacity: 0.5,
    },
    crossStyle: {
      color: 'hsl(221.2, 83.2%, 53.3%)',
      opacity: 0.5,
    },
  },
  xAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: 'hsl(214.3, 31.8%, 91.4%)',
      },
    },
    axisTick: {
      show: false,
    },
    axisLabel: {
      color: 'hsl(215.4, 16.3%, 46.9%)',
      fontSize: 11,
      margin: 12,
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: 'hsl(214.3, 31.8%, 91.4%)',
        type: 'dashed',
      },
    },
  },
  yAxis: {
    axisLine: {
      show: false,
    },
    axisTick: {
      show: false,
    },
    axisLabel: {
      color: 'hsl(215.4, 16.3%, 46.9%)',
      fontSize: 11,
      margin: 12,
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: 'hsl(214.3, 31.8%, 91.4%)',
        type: 'dashed',
      },
    },
  },
  grid: {
    left: 16,
    right: 16,
    top: 40,
    bottom: 40,
    containLabel: true,
  },
  color: CHART_COLOR_PALETTE,
};

// Dark theme configuration
export const darkTheme = {
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, system-ui, sans-serif',
    color: 'hsl(210, 40%, 98%)',
  },
  title: {
    textStyle: {
      fontWeight: 600,
      fontSize: 14,
      color: 'hsl(210, 40%, 98%)',
    },
    subtextStyle: {
      fontSize: 12,
      color: 'hsl(215, 20.2%, 65.1%)',
    },
  },
  legend: {
    textStyle: {
      color: 'hsl(215, 20.2%, 65.1%)',
      fontSize: 12,
    },
    itemGap: 16,
    itemWidth: 12,
    itemHeight: 12,
  },
  tooltip: {
    backgroundColor: 'hsl(222, 47%, 11%)',  // Solid dark, no blur
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderWidth: 1,
    borderRadius: 6,  // Was 12 - more angular
    padding: [8, 12], // Tighter padding
    textStyle: {
      color: 'hsl(210, 40%, 98%)',
      fontSize: 12,
    },
    extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.25);',  // Removed backdrop-filter
  },
  axisPointer: {
    lineStyle: {
      color: 'hsl(217.2, 91.2%, 59.8%)',
      type: 'dashed',
      opacity: 0.5,
    },
    crossStyle: {
      color: 'hsl(217.2, 91.2%, 59.8%)',
      opacity: 0.5,
    },
  },
  xAxis: {
    axisLine: {
      show: true,
      lineStyle: {
        color: 'hsl(217.2, 32.6%, 17.5%)',
      },
    },
    axisTick: {
      show: false,
    },
    axisLabel: {
      color: 'hsl(215, 20.2%, 65.1%)',
      fontSize: 11,
      margin: 12,
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: 'hsl(217.2, 32.6%, 17.5%)',
        type: 'dashed',
      },
    },
  },
  yAxis: {
    axisLine: {
      show: false,
    },
    axisTick: {
      show: false,
    },
    axisLabel: {
      color: 'hsl(215, 20.2%, 65.1%)',
      fontSize: 11,
      margin: 12,
    },
    splitLine: {
      show: true,
      lineStyle: {
        color: 'hsl(217.2, 32.6%, 17.5%)',
        type: 'dashed',
      },
    },
  },
  grid: {
    left: 16,
    right: 16,
    top: 40,
    bottom: 40,
    containLabel: true,
  },
  color: CHART_COLOR_PALETTE,
};

/**
 * Get the appropriate chart theme based on current color scheme
 */
export function getChartTheme(isDark: boolean) {
  return isDark ? darkTheme : lightTheme;
}

/**
 * Common line series styling
 */
export const lineSeriesDefaults = {
  type: 'line' as const,
  smooth: true,
  symbolSize: 6,
  lineStyle: {
    width: 2,
    cap: 'round' as const,
    join: 'round' as const,
  },
  emphasis: {
    focus: 'series' as const,
    itemStyle: {
      shadowBlur: 10,
      shadowColor: 'rgba(0, 0, 0, 0.2)',
    },
  },
};

/**
 * Common area series styling (for stacked area charts)
 */
export const areaSeriesDefaults = {
  type: 'line' as const,
  smooth: true,
  stack: 'total',
  areaStyle: {
    opacity: 0.6,
  },
  lineStyle: {
    width: 0,
  },
  symbolSize: 0,
  emphasis: {
    focus: 'series' as const,
  },
};

/**
 * Common bar series styling
 */
export const barSeriesDefaults = {
  type: 'bar' as const,
  barMaxWidth: 40,
  itemStyle: {
    borderRadius: [4, 4, 0, 0],
  },
  emphasis: {
    itemStyle: {
      shadowBlur: 10,
      shadowColor: 'rgba(0, 0, 0, 0.2)',
    },
  },
};

/**
 * Common pie series styling
 */
export const pieSeriesDefaults = {
  type: 'pie' as const,
  radius: ['45%', '70%'],
  avoidLabelOverlap: true,
  itemStyle: {
    borderRadius: 6,
    borderColor: '#fff',
    borderWidth: 2,
  },
  label: {
    show: false,
  },
  emphasis: {
    itemStyle: {
      shadowBlur: 20,
      shadowOffsetX: 0,
      shadowColor: 'rgba(0, 0, 0, 0.2)',
    },
  },
};

/**
 * Format large numbers for axis labels
 */
export function formatAxisValue(value: number): string {
  if (Math.abs(value) >= 1e9) {
    return (value / 1e9).toFixed(1) + 'B';
  }
  if (Math.abs(value) >= 1e6) {
    return (value / 1e6).toFixed(1) + 'M';
  }
  if (Math.abs(value) >= 1e3) {
    return (value / 1e3).toFixed(1) + 'K';
  }
  return value.toFixed(0);
}

/**
 * Format percentage values
 */
export function formatPercentage(value: number): string {
  return (value * 100).toFixed(1) + '%';
}

/**
 * Create gradient for area fills
 */
export function createAreaGradient(color: string, opacity: [number, number] = [0.4, 0.05]) {
  return {
    type: 'linear' as const,
    x: 0,
    y: 0,
    x2: 0,
    y2: 1,
    colorStops: [
      { offset: 0, color: color.replace(')', `, ${opacity[0]})`).replace('hsl', 'hsla') },
      { offset: 1, color: color.replace(')', `, ${opacity[1]})`).replace('hsl', 'hsla') },
    ],
  };
}

/**
 * Common tooltip formatter for time series data
 */
export function createTimeSeriesFormatter(_seriesNames: string[], valueFormatter?: (val: number) => string) {
  return (params: { name: string; seriesName: string; value: number; color: string }[]) => {
    const format = valueFormatter || ((v: number) => v.toLocaleString());
    let result = `<div style="font-weight: 600; margin-bottom: 8px;">${params[0]?.name || ''}</div>`;

    for (const item of params) {
      result += `
        <div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
          <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${item.color};"></span>
          <span style="color: var(--color-muted-foreground); flex: 1;">${item.seriesName}</span>
          <span style="font-weight: 500;">${format(item.value)}</span>
        </div>
      `;
    }

    return result;
  };
}

/**
 * Get color by index with wrap-around
 */
export function getColorByIndex(index: number): string {
  return CHART_COLOR_PALETTE[index % CHART_COLOR_PALETTE.length];
}

/**
 * Create a gradient color pair for a given base color
 */
export function getGradientPair(baseColor: string): [string, string] {
  // For now, return the same color with different opacity
  // Could be enhanced to generate actual gradient pairs
  return [baseColor, baseColor];
}
