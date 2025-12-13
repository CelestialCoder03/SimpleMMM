import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Calendar, TrendingUp, Sun } from 'lucide-react';

export interface CalendarFeaturesConfig {
  include_weekend: boolean;
  include_month: boolean;
  include_quarter: boolean;
  include_day_of_week: boolean;
}

export interface FourierFeaturesConfig {
  periods: number[];
  n_terms: number;
}

export interface SeasonalityConfig {
  enabled: boolean;
  method: 'calendar' | 'fourier' | 'both';
  calendar: CalendarFeaturesConfig;
  fourier: FourierFeaturesConfig;
}

interface SeasonalityPanelProps {
  config: SeasonalityConfig;
  onChange: (config: SeasonalityConfig) => void;
}

const DEFAULT_CONFIG: SeasonalityConfig = {
  enabled: false,
  method: 'calendar',
  calendar: {
    include_weekend: true,
    include_month: true,
    include_quarter: false,
    include_day_of_week: false,
  },
  fourier: {
    periods: [7, 30, 365],
    n_terms: 3,
  },
};

export function SeasonalityPanel({ config, onChange }: SeasonalityPanelProps) {
  // Merge with defaults
  const currentConfig = { ...DEFAULT_CONFIG, ...config };

  const updateConfig = (updates: Partial<SeasonalityConfig>) => {
    onChange({ ...currentConfig, ...updates });
  };

  const updateCalendar = (updates: Partial<CalendarFeaturesConfig>) => {
    onChange({
      ...currentConfig,
      calendar: { ...currentConfig.calendar, ...updates },
    });
  };

  const updateFourier = (updates: Partial<FourierFeaturesConfig>) => {
    onChange({
      ...currentConfig,
      fourier: { ...currentConfig.fourier, ...updates },
    });
  };

  const togglePeriod = (period: number) => {
    const periods = currentConfig.fourier.periods.includes(period)
      ? currentConfig.fourier.periods.filter(p => p !== period)
      : [...currentConfig.fourier.periods, period].sort((a, b) => a - b);
    updateFourier({ periods });
  };

  // Count features that will be generated
  const getFeatureCount = () => {
    if (!currentConfig.enabled) return 0;
    
    let count = 0;
    const cal = currentConfig.calendar;
    const fou = currentConfig.fourier;
    
    if (currentConfig.method === 'calendar' || currentConfig.method === 'both') {
      if (cal.include_weekend) count += 1;
      if (cal.include_month) count += 11; // 12 months - 1 reference
      if (cal.include_quarter) count += 3; // 4 quarters - 1 reference
      if (cal.include_day_of_week) count += 6; // 7 days - 1 reference
    }
    
    if (currentConfig.method === 'fourier' || currentConfig.method === 'both') {
      count += fou.periods.length * fou.n_terms * 2; // sin + cos for each
    }
    
    return count;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sun className="h-5 w-5 text-orange-500" />
            <div>
              <CardTitle className="text-lg">季节性特征 / Seasonality</CardTitle>
              <CardDescription>
                自动生成季节性特征以捕捉周期性模式
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={currentConfig.enabled}
              onCheckedChange={(enabled) => updateConfig({ enabled })}
            />
            <Label>{currentConfig.enabled ? '已启用' : '未启用'}</Label>
          </div>
        </div>
      </CardHeader>
      
      {currentConfig.enabled && (
        <CardContent className="space-y-6">
          {/* Method Selection */}
          <div className="space-y-3">
            <Label className="text-sm font-medium">生成方法</Label>
            <div className="flex gap-2">
              {[
                { value: 'calendar' as const, label: '日历Dummy', icon: Calendar },
                { value: 'fourier' as const, label: '傅里叶特征', icon: TrendingUp },
                { value: 'both' as const, label: '两者都用', icon: null },
              ].map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  onClick={() => updateConfig({ method: value })}
                  className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-md border transition-colors ${
                    currentConfig.method === value
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-muted border-input'
                  }`}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Calendar Features */}
          {(currentConfig.method === 'calendar' || currentConfig.method === 'both') && (
            <div className="space-y-3 p-4 bg-muted/50 rounded-lg">
              <Label className="text-sm font-medium flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                日历特征选项
              </Label>
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="weekend" className="text-sm">
                    周末/工作日 (is_weekend)
                  </Label>
                  <Switch
                    id="weekend"
                    checked={currentConfig.calendar.include_weekend}
                    onCheckedChange={(include_weekend) => updateCalendar({ include_weekend })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="month" className="text-sm">
                    月份 (month_2 ~ month_12)
                  </Label>
                  <Switch
                    id="month"
                    checked={currentConfig.calendar.include_month}
                    onCheckedChange={(include_month) => updateCalendar({ include_month })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="quarter" className="text-sm">
                    季度 (quarter_2 ~ quarter_4)
                  </Label>
                  <Switch
                    id="quarter"
                    checked={currentConfig.calendar.include_quarter}
                    onCheckedChange={(include_quarter) => updateCalendar({ include_quarter })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="dow" className="text-sm">
                    星期几 (dow_1 ~ dow_6)
                  </Label>
                  <Switch
                    id="dow"
                    checked={currentConfig.calendar.include_day_of_week}
                    onCheckedChange={(include_day_of_week) => updateCalendar({ include_day_of_week })}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Fourier Features */}
          {(currentConfig.method === 'fourier' || currentConfig.method === 'both') && (
            <div className="space-y-3 p-4 bg-muted/50 rounded-lg">
              <Label className="text-sm font-medium flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                傅里叶特征选项
              </Label>
              
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-sm">周期选择</Label>
                  <div className="flex gap-2 flex-wrap">
                    {[7, 30, 90, 365].map(period => (
                      <button
                        key={period}
                        onClick={() => togglePeriod(period)}
                        className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                          currentConfig.fourier.periods.includes(period)
                            ? 'bg-primary text-primary-foreground border-primary'
                            : 'bg-background hover:bg-muted border-input'
                        }`}
                      >
                        {period === 7 ? '7天 (周)' : 
                         period === 30 ? '30天 (月)' : 
                         period === 90 ? '90天 (季)' : 
                         '365天 (年)'}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <Label className="text-sm">傅里叶项数: {currentConfig.fourier.n_terms}</Label>
                    <span className="text-xs text-muted-foreground">
                      (每个周期生成 {currentConfig.fourier.n_terms * 2} 个特征)
                    </span>
                  </div>
                  <Slider
                    value={[currentConfig.fourier.n_terms]}
                    onValueChange={([n_terms]) => updateFourier({ n_terms })}
                    min={1}
                    max={10}
                    step={1}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Feature Count Summary */}
          <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center gap-2 text-sm text-blue-700 dark:text-blue-300">
              <span className="font-medium">预计生成特征数:</span>
              <span className="text-lg font-bold">{getFeatureCount()}</span>
              <span className="text-muted-foreground">个季节性特征将自动添加到模型中</span>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export { DEFAULT_CONFIG as DEFAULT_SEASONALITY_CONFIG };
