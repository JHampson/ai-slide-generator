/**
 * Tool Library Form - Modal form for creating/editing tools.
 * 
 * Shows type-specific configuration fields based on the selected tool type.
 */

import React, { useState, useEffect } from 'react';
import { configApi, ConfigApiError } from '../../api/config';
import type { ToolLibraryItem, ToolLibraryCreate, ToolType } from '../../api/config';
import { GenieToolConfig } from './tools/GenieToolConfig';
import { VectorToolConfig } from './tools/VectorToolConfig';
import { MCPToolConfig } from './tools/MCPToolConfig';
import { UCFunctionToolConfig } from './tools/UCFunctionToolConfig';

interface ToolLibraryFormProps {
  tool: ToolLibraryItem | null;
  onSave: () => void;
  onClose: () => void;
}

const TOOL_TYPES: { value: ToolType; label: string; icon: string; description: string }[] = [
  { 
    value: 'genie_space', 
    label: 'Genie Space', 
    icon: '🧞',
    description: 'Query data using Databricks Genie natural language interface'
  },
  { 
    value: 'vector_index', 
    label: 'Vector Index', 
    icon: '🔍',
    description: 'Search documents using Databricks Vector Search'
  },
  { 
    value: 'mcp_server', 
    label: 'MCP Server', 
    icon: '🔌',
    description: 'Connect to external tools via Model Context Protocol'
  },
  { 
    value: 'uc_function', 
    label: 'UC Function', 
    icon: '⚡',
    description: 'Execute Unity Catalog SQL functions'
  },
];

export const ToolLibraryForm: React.FC<ToolLibraryFormProps> = ({
  tool,
  onSave,
  onClose,
}) => {
  const isEditing = !!tool;
  
  // Form state
  const [toolType, setToolType] = useState<ToolType>(tool?.tool_type || 'genie_space');
  const [name, setName] = useState(tool?.name || '');
  const [description, setDescription] = useState(tool?.description || '');
  const [config, setConfig] = useState<Record<string, unknown>>(tool?.config || {});
  
  // UI state
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Reset config when tool type changes (only for new tools)
  useEffect(() => {
    if (!isEditing) {
      setConfig({});
    }
  }, [toolType, isEditing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setValidationErrors([]);

    // Basic validation
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    // Validate config
    try {
      const validation = await configApi.validateToolConfig({
        tool_type: toolType,
        config,
      });
      
      if (!validation.valid) {
        setValidationErrors(validation.errors);
        return;
      }
    } catch (err) {
      // Continue if validation endpoint fails
      console.warn('Config validation failed:', err);
    }

    try {
      setSaving(true);

      if (isEditing && tool) {
        await configApi.updateTool(tool.id, {
          name: name.trim(),
          description: description.trim() || null,
          config,
        });
      } else {
        const createData: ToolLibraryCreate = {
          tool_type: toolType,
          name: name.trim(),
          description: description.trim() || null,
          config,
        };
        await configApi.createTool(createData);
      }

      onSave();
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to save tool';
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleConfigChange = (newConfig: Record<string, unknown>) => {
    setConfig(newConfig);
  };

  const renderConfigFields = () => {
    switch (toolType) {
      case 'genie_space':
        return (
          <GenieToolConfig
            config={config}
            onChange={handleConfigChange}
          />
        );
      case 'vector_index':
        return (
          <VectorToolConfig
            config={config}
            onChange={handleConfigChange}
          />
        );
      case 'mcp_server':
        return (
          <MCPToolConfig
            config={config}
            onChange={handleConfigChange}
          />
        );
      case 'uc_function':
        return (
          <UCFunctionToolConfig
            config={config}
            onChange={handleConfigChange}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        {/* Backdrop */}
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          onClick={onClose}
        />
        
        {/* Modal */}
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              {isEditing ? 'Edit Tool' : 'Add Tool'}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500"
            >
              <span className="text-2xl">&times;</span>
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* Error display */}
            {(error || validationErrors.length > 0) && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                {error && <p className="text-red-700">{error}</p>}
                {validationErrors.length > 0 && (
                  <ul className="list-disc list-inside text-red-700">
                    {validationErrors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Tool Type Selection (only for new tools) */}
            {!isEditing && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Tool Type
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {TOOL_TYPES.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => setToolType(type.value)}
                      className={`p-4 text-left border rounded-lg transition-colors ${
                        toolType === type.value
                          ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-500'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center mb-1">
                        <span className="text-xl mr-2">{type.icon}</span>
                        <span className="font-medium text-gray-900">{type.label}</span>
                      </div>
                      <p className="text-xs text-gray-500">{type.description}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Tool type badge for editing */}
            {isEditing && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tool Type
                </label>
                <div className="flex items-center">
                  <span className="text-xl mr-2">
                    {TOOL_TYPES.find(t => t.value === toolType)?.icon}
                  </span>
                  <span className="text-gray-900">
                    {TOOL_TYPES.find(t => t.value === toolType)?.label}
                  </span>
                </div>
              </div>
            )}

            {/* Name */}
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Sales Data Genie"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                A unique name for this tool. Used in the tool library and profile assignments.
              </p>
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what data or functionality this tool provides..."
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                This description is shown to the AI agent to help it understand when to use this tool.
              </p>
            </div>

            {/* Type-specific configuration */}
            <div className="border-t pt-6">
              <h3 className="text-sm font-medium text-gray-700 mb-4">
                Configuration
              </h3>
              {renderConfigFields()}
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 hover:text-gray-900"
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Tool'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
