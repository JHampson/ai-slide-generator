/**
 * Unity Catalog Function Tool Configuration Form.
 * 
 * Configures execution of a Unity Catalog SQL function.
 */

import React from 'react';

interface UCFunctionToolConfigProps {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export const UCFunctionToolConfig: React.FC<UCFunctionToolConfigProps> = ({
  config,
  onChange,
}) => {
  const catalog = (config.catalog as string) || '';
  const schema = (config.schema as string) || '';
  const functionName = (config.function_name as string) || '';
  const warehouseId = (config.warehouse_id as string) || '';

  const handleFieldChange = (field: string, value: string) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  // Build the full function path for display
  const fullPath = [catalog, schema, functionName].filter(Boolean).join('.');

  return (
    <div className="space-y-4">
      {/* Function Path Preview */}
      {fullPath && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-md">
          <p className="text-sm text-gray-600">Function Path:</p>
          <p className="font-mono text-sm text-gray-900">{fullPath}</p>
        </div>
      )}

      {/* Catalog */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Catalog <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={catalog}
          onChange={(e) => handleFieldChange('catalog', e.target.value)}
          placeholder="main"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          The Unity Catalog catalog containing the function.
        </p>
      </div>

      {/* Schema */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Schema <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={schema}
          onChange={(e) => handleFieldChange('schema', e.target.value)}
          placeholder="default"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          The schema containing the function.
        </p>
      </div>

      {/* Function Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Function Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={functionName}
          onChange={(e) => handleFieldChange('function_name', e.target.value)}
          placeholder="my_function"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          The name of the SQL function to execute.
        </p>
      </div>

      {/* SQL Warehouse */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          SQL Warehouse ID
        </label>
        <input
          type="text"
          value={warehouseId}
          onChange={(e) => handleFieldChange('warehouse_id', e.target.value)}
          placeholder="abc123def456"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          SQL warehouse to execute the function. If empty, uses DATABRICKS_SQL_WAREHOUSE_ID env var or auto-detects.
        </p>
      </div>

      {/* Info Box */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-800">
          <strong>Permissions:</strong> When running in Databricks Apps with user token passthrough, 
          the function runs with the user's permissions. Otherwise, it uses the app's service principal.
        </p>
      </div>
    </div>
  );
};
