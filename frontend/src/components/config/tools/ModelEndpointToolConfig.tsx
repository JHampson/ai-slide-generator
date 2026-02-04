/**
 * Model Serving Endpoint Tool Configuration Form.
 * 
 * Configures querying of a Databricks Model Serving endpoint.
 */

import React, { useEffect, useState } from 'react';
import { configApi } from '../../../api/config';

interface ModelEndpointToolConfigProps {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

interface EndpointInfo {
  name: string;
  state: string;
  creator?: string;
}

export const ModelEndpointToolConfig: React.FC<ModelEndpointToolConfigProps> = ({
  config,
  onChange,
}) => {
  const endpointName = (config.endpoint_name as string) || '';
  
  const [availableEndpoints, setAvailableEndpoints] = useState<Record<string, EndpointInfo>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load available endpoints on mount
  useEffect(() => {
    const loadEndpoints = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await configApi.discoverModelEndpoints();
        setAvailableEndpoints(data.endpoints || {});
      } catch (err) {
        console.error('Failed to load model endpoints:', err);
        setError('Failed to load available endpoints');
      } finally {
        setLoading(false);
      }
    };

    loadEndpoints();
  }, []);

  const handleFieldChange = (field: string, value: string) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  const handleEndpointSelect = (name: string) => {
    onChange({
      ...config,
      endpoint_name: name,
    });
  };

  // Sort endpoints by name
  const sortedEndpoints = Object.values(availableEndpoints).sort((a, b) => 
    a.name.localeCompare(b.name)
  );

  return (
    <div className="space-y-4">
      {/* Endpoint Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Model Serving Endpoint <span className="text-red-500">*</span>
        </label>
        
        {loading ? (
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
            <p className="text-sm text-gray-500">Loading available endpoints...</p>
          </div>
        ) : error ? (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        ) : sortedEndpoints.length > 0 ? (
          <div className="space-y-2">
            <select
              value={endpointName}
              onChange={(e) => handleEndpointSelect(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select an endpoint...</option>
              {sortedEndpoints.map((endpoint) => (
                <option key={endpoint.name} value={endpoint.name}>
                  {endpoint.name} ({endpoint.state})
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500">
              Or enter a custom endpoint name below
            </p>
          </div>
        ) : null}

        {/* Manual endpoint name input */}
        <div className="mt-2">
          <input
            type="text"
            value={endpointName}
            onChange={(e) => handleFieldChange('endpoint_name', e.target.value)}
            placeholder="my-model-endpoint"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <p className="mt-1 text-xs text-gray-500">
          The name of the Databricks Model Serving endpoint to query.
        </p>
      </div>

      {/* Selected Endpoint Info */}
      {endpointName && availableEndpoints[endpointName] && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
          <p className="text-sm text-gray-600">Selected Endpoint:</p>
          <p className="font-medium text-gray-900">{endpointName}</p>
          <p className="text-xs text-gray-500 mt-1">
            State: {availableEndpoints[endpointName].state}
          </p>
        </div>
      )}

      {/* Info Box */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-800">
          <strong>Permissions:</strong> The model endpoint will be queried using the current user's 
          OAuth token, ensuring access controls are respected. The user must have permission to 
          query the endpoint.
        </p>
      </div>

      {/* Input Schema Info */}
      <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
        <p className="text-sm text-gray-700">
          <strong>Input Schema:</strong> The input schema for the model is automatically inferred. 
          The LLM will pass input data as key-value pairs matching the model's expected format.
        </p>
      </div>
    </div>
  );
};
