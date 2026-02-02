/**
 * Vector Index Tool Configuration Form.
 * 
 * Configures a Databricks Vector Search index for document retrieval.
 */

import React, { useState } from 'react';
import { configApi, ConfigApiError } from '../../../api/config';

interface VectorToolConfigProps {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

interface VectorIndex {
  endpoint_name: string;
  index_name: string;
  endpoint_status?: string;
  index_type?: string;
}

export const VectorToolConfig: React.FC<VectorToolConfigProps> = ({
  config,
  onChange,
}) => {
  const [availableIndexes, setAvailableIndexes] = useState<Record<string, VectorIndex> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const endpointName = (config.endpoint_name as string) || '';
  const indexName = (config.index_name as string) || '';
  const numResults = (config.num_results as number) || 5;
  const columns = (config.columns as string) || '';

  const loadIndexes = async () => {
    if (availableIndexes) return;

    try {
      setLoading(true);
      setError(null);
      const result = await configApi.discoverVectorIndexes();
      setAvailableIndexes(result.indexes);
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to load vector indexes';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleIndexSelect = (key: string) => {
    const index = availableIndexes?.[key];
    if (index) {
      onChange({
        ...config,
        endpoint_name: index.endpoint_name,
        index_name: index.index_name,
      });
    }
  };

  const handleFieldChange = (field: string, value: string | number) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  // Create composite key for dropdown
  const selectedKey = endpointName && indexName ? `${endpointName}/${indexName}` : '';

  return (
    <div className="space-y-4">
      {/* Index Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Vector Search Index
        </label>
        <select
          value={selectedKey}
          onChange={(e) => handleIndexSelect(e.target.value)}
          onFocus={loadIndexes}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Select an index or enter manually...</option>
          {loading && <option disabled>Loading indexes...</option>}
          {availableIndexes && Object.entries(availableIndexes).map(([key, index]) => (
            <option key={key} value={key}>
              {key} {index.endpoint_status ? `(${index.endpoint_status})` : ''}
            </option>
          ))}
        </select>
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>

      {/* Manual Entry */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Endpoint Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={endpointName}
            onChange={(e) => handleFieldChange('endpoint_name', e.target.value)}
            placeholder="vs-endpoint-name"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Index Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={indexName}
            onChange={(e) => handleFieldChange('index_name', e.target.value)}
            placeholder="catalog.schema.index"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>

      {/* Number of Results */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Number of Results
        </label>
        <input
          type="number"
          value={numResults}
          onChange={(e) => handleFieldChange('num_results', parseInt(e.target.value) || 5)}
          min={1}
          max={20}
          className="w-32 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Default number of search results to return (1-20).
        </p>
      </div>

      {/* Columns to Return */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Columns to Return <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={columns}
          onChange={(e) => handleFieldChange('columns', e.target.value)}
          placeholder="text_content, title, url"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Comma-separated list of column names to return from search results.
          Check your index schema for available columns.
        </p>
      </div>

      {/* Info Box */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-800">
          <strong>Permissions:</strong> Vector search uses the user's permissions when running 
          with user token passthrough enabled. Otherwise, it uses the app's service principal.
        </p>
      </div>
    </div>
  );
};
