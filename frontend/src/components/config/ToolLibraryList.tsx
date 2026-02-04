/**
 * Tool Library List - Table component for displaying tools.
 * 
 * Shows all tools in the library with type badges, descriptions,
 * and action buttons for editing and deleting.
 */

import React from 'react';
import type { ToolLibraryItem, ToolType } from '../../api/config';

interface ToolLibraryListProps {
  tools: ToolLibraryItem[];
  onEdit: (tool: ToolLibraryItem) => void;
  onDelete: (tool: ToolLibraryItem) => void;
}

const TOOL_TYPE_LABELS: Record<ToolType, string> = {
  genie_space: 'Genie Space',
  vector_index: 'Vector Index',
  mcp_server: 'MCP Server',
  uc_function: 'UC Function',
  model_endpoint: 'Model Endpoint',
};

const TOOL_TYPE_COLORS: Record<ToolType, string> = {
  genie_space: 'bg-purple-100 text-purple-800',
  vector_index: 'bg-blue-100 text-blue-800',
  mcp_server: 'bg-green-100 text-green-800',
  uc_function: 'bg-orange-100 text-orange-800',
  model_endpoint: 'bg-teal-100 text-teal-800',
};

const TOOL_TYPE_ICONS: Record<ToolType, string> = {
  genie_space: '🧞',
  vector_index: '🔍',
  mcp_server: '🔌',
  uc_function: '⚡',
  model_endpoint: '🤖',
};

export const ToolLibraryList: React.FC<ToolLibraryListProps> = ({
  tools,
  onEdit,
  onDelete,
}) => {
  if (tools.length === 0) {
    return (
      <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-gray-500 mb-4">No tools in the library yet.</p>
        <p className="text-sm text-gray-400">
          Click "Add Tool" to create your first tool.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Description
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {tools.map((tool) => (
            <tr 
              key={tool.id} 
              className="hover:bg-gray-50 cursor-pointer"
              onClick={() => onEdit(tool)}
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <span className="text-lg mr-2">{TOOL_TYPE_ICONS[tool.tool_type]}</span>
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {tool.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {getToolConfigSummary(tool)}
                    </div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${TOOL_TYPE_COLORS[tool.tool_type]}`}>
                  {TOOL_TYPE_LABELS[tool.tool_type]}
                </span>
              </td>
              <td className="px-6 py-4">
                <div className="text-sm text-gray-500 max-w-xs truncate">
                  {tool.description || <span className="italic text-gray-400">No description</span>}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {tool.is_active ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    Inactive
                  </span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <button
                  onClick={(e) => { e.stopPropagation(); onEdit(tool); }}
                  className="text-blue-600 hover:text-blue-900 hover:underline cursor-pointer mr-4"
                >
                  Edit
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onDelete(tool); }}
                  className="text-red-600 hover:text-red-900 hover:underline cursor-pointer"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

/**
 * Get a brief summary of the tool's configuration for display.
 */
function getToolConfigSummary(tool: ToolLibraryItem): string {
  const config = tool.config;
  
  switch (tool.tool_type) {
    case 'genie_space':
      return config.space_name as string || config.space_id as string || 'Genie';
    case 'vector_index':
      return `${config.endpoint_name || ''}/${config.index_name || ''}`;
    case 'mcp_server':
      return config.url as string || 'MCP Server';
    case 'uc_function':
      return `${config.catalog || ''}.${config.schema || ''}.${config.function_name || ''}`;
    default:
      return '';
  }
}
