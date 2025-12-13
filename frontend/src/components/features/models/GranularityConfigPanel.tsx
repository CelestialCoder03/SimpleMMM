import { useState } from 'react';
import { Plus, Trash2, Info, Layers } from 'lucide-react';
import { Button, Card, Label } from '@/components/ui';

interface GranularityDimension {
  column: string;
  type: 'categorical' | 'hierarchical';
  parent?: string;
}

interface GranularityConfig {
  level: string;
  dimensions: GranularityDimension[];
  hierarchy_type: 'no_pooling' | 'complete_pooling' | 'partial_pooling';
  varying_coefficients?: {
    by_region?: string[];
    by_channel?: string[];
    fixed?: string[];
  };
}

interface GranularityConfigPanelProps {
  availableColumns: string[];
  featureColumns: string[];
  config: GranularityConfig;
  onChange: (config: GranularityConfig) => void;
  disabled?: boolean;
}

const GRANULARITY_LEVELS = [
  { value: 'national', label: 'National', description: 'Single aggregate model' },
  { value: 'regional', label: 'Regional', description: 'Model by region/geography' },
  { value: 'channel', label: 'Channel', description: 'Model by sales channel' },
  { value: 'product', label: 'Product', description: 'Model by product category' },
  { value: 'custom', label: 'Custom', description: 'Define custom dimensions' },
];

const HIERARCHY_TYPES = [
  { 
    value: 'no_pooling', 
    label: 'No Pooling',
    description: 'Separate models for each segment (most flexible, needs more data)',
  },
  { 
    value: 'complete_pooling', 
    label: 'Complete Pooling',
    description: 'Single model for all segments (simplest, assumes same effects)',
  },
  { 
    value: 'partial_pooling', 
    label: 'Partial Pooling',
    description: 'Hierarchical model with information sharing (recommended)',
  },
];

export function GranularityConfigPanel({
  availableColumns,
  featureColumns,
  config,
  onChange,
  disabled = false,
}: GranularityConfigPanelProps) {
  const [newDimensionColumn, setNewDimensionColumn] = useState('');

  const handleLevelChange = (level: string) => {
    onChange({ ...config, level });
  };

  const handleHierarchyTypeChange = (hierarchy_type: GranularityConfig['hierarchy_type']) => {
    onChange({ ...config, hierarchy_type });
  };

  const handleAddDimension = () => {
    if (!newDimensionColumn) return;
    
    const newDimension: GranularityDimension = {
      column: newDimensionColumn,
      type: 'categorical',
    };
    
    onChange({
      ...config,
      dimensions: [...config.dimensions, newDimension],
    });
    setNewDimensionColumn('');
  };

  const handleRemoveDimension = (index: number) => {
    const newDimensions = config.dimensions.filter((_, i) => i !== index);
    onChange({ ...config, dimensions: newDimensions });
  };

  const handleDimensionTypeChange = (index: number, type: 'categorical' | 'hierarchical') => {
    const newDimensions = [...config.dimensions];
    newDimensions[index] = { ...newDimensions[index], type };
    onChange({ ...config, dimensions: newDimensions });
  };

  const handleVaryingCoefficientToggle = (feature: string, category: 'by_region' | 'fixed') => {
    const currentVarying = config.varying_coefficients || { by_region: [], fixed: [] };
    const currentList = currentVarying[category] || [];
    
    let newList: string[];
    if (currentList.includes(feature)) {
      newList = currentList.filter((f) => f !== feature);
    } else {
      newList = [...currentList, feature];
    }
    
    onChange({
      ...config,
      varying_coefficients: {
        ...currentVarying,
        [category]: newList,
      },
    });
  };

  const usedColumns = config.dimensions.map((d) => d.column);
  const availableDimensionColumns = availableColumns.filter(
    (col) => !usedColumns.includes(col) && !featureColumns.includes(col)
  );

  const isMultiGranularity = config.level !== 'national' || config.dimensions.length > 0;

  return (
    <Card className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Layers className="h-5 w-5 text-gray-500" />
        <h4 className="text-sm font-medium">Granularity Settings</h4>
        <div className="group relative">
          <Info className="h-4 w-4 text-gray-400 cursor-help" />
          <div className="absolute left-0 top-6 w-72 p-2 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10">
            Multi-granularity modeling allows you to build models at different levels 
            (e.g., regional, channel) while sharing information across segments.
          </div>
        </div>
      </div>

      {/* Granularity Level */}
      <div className="mb-4">
        <Label>Granularity Level</Label>
        <select
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
          value={config.level}
          onChange={(e) => handleLevelChange(e.target.value)}
          disabled={disabled}
        >
          {GRANULARITY_LEVELS.map((level) => (
            <option key={level.value} value={level.value}>
              {level.label}
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">
          {GRANULARITY_LEVELS.find((l) => l.value === config.level)?.description}
        </p>
      </div>

      {/* Dimensions */}
      {config.level !== 'national' && (
        <div className="mb-4">
          <Label>Dimensions</Label>
          
          {/* Add dimension */}
          {!disabled && availableDimensionColumns.length > 0 && (
            <div className="flex gap-2 mt-2 mb-3">
              <select
                className="flex-1 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
                value={newDimensionColumn}
                onChange={(e) => setNewDimensionColumn(e.target.value)}
              >
                <option value="">Select column...</option>
                {availableDimensionColumns.map((col) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
              <Button
                size="sm"
                onClick={handleAddDimension}
                disabled={!newDimensionColumn}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add
              </Button>
            </div>
          )}

          {/* Dimension list */}
          <div className="space-y-2">
            {config.dimensions.map((dimension, index) => (
              <div key={index} className="flex items-center gap-2 p-2 bg-gray-50 rounded">
                <span className="flex-1 text-sm font-medium">{dimension.column}</span>
                <select
                  className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-xs"
                  value={dimension.type}
                  onChange={(e) => handleDimensionTypeChange(index, e.target.value as 'categorical' | 'hierarchical')}
                  disabled={disabled}
                >
                  <option value="categorical">Categorical</option>
                  <option value="hierarchical">Hierarchical</option>
                </select>
                {!disabled && (
                  <button
                    onClick={() => handleRemoveDimension(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}

            {config.dimensions.length === 0 && (
              <p className="text-sm text-gray-500 py-2">
                No dimensions added. Add a column to segment your model.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Hierarchy Type */}
      {isMultiGranularity && (
        <div className="mb-4">
          <Label>Hierarchy Type</Label>
          <select
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
            value={config.hierarchy_type}
            onChange={(e) => handleHierarchyTypeChange(e.target.value as GranularityConfig['hierarchy_type'])}
            disabled={disabled}
          >
            {HIERARCHY_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {HIERARCHY_TYPES.find((t) => t.value === config.hierarchy_type)?.description}
          </p>
        </div>
      )}

      {/* Varying Coefficients */}
      {isMultiGranularity && config.hierarchy_type === 'partial_pooling' && featureColumns.length > 0 && (
        <div>
          <Label>Varying Coefficients</Label>
          <p className="text-xs text-gray-500 mb-2">
            Select which coefficients should vary by segment vs. stay fixed across all segments.
          </p>
          
          <div className="space-y-1 max-h-40 overflow-y-auto border rounded p-2">
            {featureColumns.map((feature) => {
              const isVarying = config.varying_coefficients?.by_region?.includes(feature);
              const isFixed = config.varying_coefficients?.fixed?.includes(feature);
              
              return (
                <div key={feature} className="flex items-center justify-between py-1">
                  <span className="text-sm">{feature}</span>
                  <div className="flex gap-2">
                    <label className="flex items-center gap-1 text-xs">
                      <input
                        type="radio"
                        name={`varying-${feature}`}
                        checked={isVarying}
                        onChange={() => handleVaryingCoefficientToggle(feature, 'by_region')}
                        disabled={disabled}
                      />
                      Varying
                    </label>
                    <label className="flex items-center gap-1 text-xs">
                      <input
                        type="radio"
                        name={`varying-${feature}`}
                        checked={isFixed}
                        onChange={() => handleVaryingCoefficientToggle(feature, 'fixed')}
                        disabled={disabled}
                      />
                      Fixed
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}

export default GranularityConfigPanel;
