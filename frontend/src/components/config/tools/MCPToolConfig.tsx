/**
 * MCP Server Tool Configuration Form.
 * 
 * Configures connection to an external MCP (Model Context Protocol) server
 * via Databricks MCP proxy using Unity Catalog connections.
 */

import React from 'react';

interface MCPToolConfigProps {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export const MCPToolConfig: React.FC<MCPToolConfigProps> = ({
  config,
  onChange,
}) => {
  const connectionName = (config.connection_name as string) || '';

  const handleFieldChange = (field: string, value: string) => {
    onChange({
      ...config,
      [field]: value,
    });
  };

  return (
    <div className="space-y-4">
      {/* Unity Catalog Connection Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Unity Catalog Connection Name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={connectionName}
          onChange={(e) => handleFieldChange('connection_name', e.target.value)}
          placeholder="tavily-mcp"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          The Unity Catalog connection name for the external MCP server.
        </p>
      </div>

      {/* Instructions Box */}
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-md space-y-3">
        <p className="text-sm font-medium text-blue-900">
          Setting up an External MCP Connection
        </p>
        <ol className="text-sm text-blue-800 list-decimal list-inside space-y-2">
          <li>Go to Databricks UI &rarr; <strong>Catalog</strong> &rarr; <strong>External Connections</strong></li>
          <li>Click <strong>Create Connection</strong></li>
          <li>Configure the connection:
            <ul className="ml-6 mt-1 list-disc list-inside text-xs space-y-1">
              <li><strong>Name:</strong> e.g., <code className="bg-blue-100 px-1 rounded">tavily-mcp</code></li>
              <li><strong>Type:</strong> HTTP</li>
              <li><strong>URL:</strong> The MCP server URL (e.g., <code className="bg-blue-100 px-1 rounded">https://mcp.tavily.com/mcp</code>)</li>
              <li><strong>Authentication:</strong> Bearer token with your API key</li>
            </ul>
          </li>
          <li>Enter the connection name above</li>
        </ol>
      </div>

      {/* Security Note */}
      <div className="p-3 bg-green-50 border border-green-200 rounded-md">
        <p className="text-sm text-green-800">
          <strong>Security:</strong> API keys are stored securely in Unity Catalog connections, 
          not in the app database. Access is controlled by Unity Catalog permissions.
        </p>
      </div>
    </div>
  );
};
