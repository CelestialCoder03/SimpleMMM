import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import ReactECharts from 'echarts-for-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';

interface AdstockConfig {
  type: string;
  decay: number;
  max_lag: number;
}

interface SaturationConfig {
  type: string;
  k: number | 'auto';
  s: number | 'auto';
}

interface TransformationPreviewProps {
  featureName: string;
  originalData: number[];
  adstock: AdstockConfig;
  saturation: SaturationConfig;
  adstockEnabled?: boolean;
  saturationEnabled?: boolean;
}

// Geometric adstock transformation
function applyAdstock(data: number[], decay: number, maxLag: number): number[] {
  const result: number[] = [];
  
  for (let t = 0; t < data.length; t++) {
    let adstockedValue = 0;
    for (let lag = 0; lag <= Math.min(t, maxLag); lag++) {
      adstockedValue += data[t - lag] * Math.pow(decay, lag);
    }
    result.push(adstockedValue);
  }
  
  return result;
}

// Hill saturation transformation
function applySaturation(data: number[], k: number, s: number): number[] {
  // Normalize data first
  const maxVal = Math.max(...data);
  if (maxVal === 0) return data;
  
  return data.map((x) => {
    const normalized = x / maxVal;
    // Hill function: x^s / (k^s + x^s)
    const powered = Math.pow(normalized, s);
    return powered / (Math.pow(k, s) + powered);
  });
}

interface SeriesItem {
  name: string;
  type: string;
  data: number[];
  smooth: boolean;
  symbol: string;
  lineStyle: { width: number; type?: string; color: string };
}

export function TransformationPreview({
  featureName,
  originalData,
  adstock,
  saturation,
  adstockEnabled = true,
  saturationEnabled = true,
}: TransformationPreviewProps) {
  const { t } = useTranslation();

  const chartOption = useMemo(() => {
    if (!originalData || originalData.length === 0) {
      return null;
    }

    // Apply transformations only if enabled
    const adstocked = adstockEnabled 
      ? applyAdstock(originalData, adstock.decay, adstock.max_lag)
      : originalData;
    
    // Use default values for auto parameters
    const kValue = saturation.k === 'auto' ? 0.5 : saturation.k;
    const sValue = saturation.s === 'auto' ? 1.0 : saturation.s;
    const transformed = saturationEnabled 
      ? applySaturation(adstocked, kValue, sValue)
      : adstocked;

    // Use raw values instead of normalized for better user understanding
    const periods = originalData.map((_, i) => i + 1);
    
    // Find max value for Y-axis scaling
    const allValues = [...originalData, ...adstocked];
    const maxValue = Math.max(...allValues);

    // Build series dynamically based on enabled transformations
    const series: SeriesItem[] = [
      {
        name: t('transformations.original'),
        type: 'line',
        data: originalData,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, type: 'dashed', color: '#9ca3af' },
      },
    ];

    if (adstockEnabled) {
      series.push({
        name: t('transformations.afterAdstock'),
        type: 'line',
        data: adstocked,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#3b82f6' },
      });
    }

    if (saturationEnabled) {
      // Scale saturation values back to original scale for display
      const saturationScaled = transformed.map(v => v * maxValue);
      series.push({
        name: t('transformations.afterSaturation'),
        type: 'line',
        data: saturationScaled,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#16a34a' },
      });
    }

    return {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e5e7eb',
        borderWidth: 1,
        textStyle: { fontSize: 12 },
        formatter: (params: Array<{ seriesName: string; value: number; marker: string; dataIndex?: number }>) => {
          const idx = params[0]?.dataIndex ?? 0;
          return `
            <div style="font-weight: 500; margin-bottom: 4px;">${t('transformations.period')} ${idx + 1}</div>
            ${params.map((p) => `
              <div style="display: flex; align-items: center; gap: 4px;">
                ${p.marker}
                <span>${p.seriesName}: ${typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</span>
              </div>
            `).join('')}
          `;
        },
      },
      legend: {
        bottom: 0,
        textStyle: { fontSize: 11 },
        itemWidth: 20,
        itemHeight: 2,
      },
      grid: {
        top: 10,
        right: 20,
        bottom: 50,
        left: 60,
      },
      xAxis: {
        type: 'category',
        data: periods,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 10 },
        name: t('transformations.period'),
        nameLocation: 'middle',
        nameGap: 25,
        nameTextStyle: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { fontSize: 10 },
        splitLine: { lineStyle: { type: 'dashed', color: '#e5e7eb' } },
        name: t('transformations.value'),
        nameLocation: 'middle',
        nameGap: 45,
        nameTextStyle: { fontSize: 11 },
      },
      series,
    };
  }, [originalData, adstock.decay, adstock.max_lag, saturation.k, saturation.s, adstockEnabled, saturationEnabled, t]);

  if (!originalData || originalData.length === 0 || !chartOption) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <p className="text-sm text-muted-foreground">
            {t('transformations.noDataForPreview')}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-primary" />
          <CardTitle className="text-base">{t('transformations.preview')}</CardTitle>
        </div>
        <CardDescription>
          {t('transformations.previewDesc', { feature: featureName })}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64">
          <ReactECharts
            option={chartOption}
            style={{ height: '100%', width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        </div>

        <div className="mt-3 flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <div className="h-0.5 w-4 bg-muted-foreground" style={{ borderStyle: 'dashed' }} />
            <span className="text-muted-foreground">{t('transformations.original')}</span>
          </div>
          {adstockEnabled && (
            <div className="flex items-center gap-1.5">
              <div className="h-0.5 w-4 bg-blue-500" />
              <span className="text-muted-foreground">
                {t('transformations.adstock')} (λ={adstock.decay})
              </span>
            </div>
          )}
          {saturationEnabled && (
            <div className="flex items-center gap-1.5">
              <div className="h-0.5 w-4 bg-green-600" />
              <span className="text-muted-foreground">
                {t('transformations.saturation')} ({saturation.type})
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default TransformationPreview;
