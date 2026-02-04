/**
 * Profile Tools Form - Manages tool assignments for a profile.
 * 
 * Allows adding tools from the library to a profile, enabling/disabling them,
 * and managing their priority order.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { configApi, ConfigApiError } from '../../api/config';
import type { ProfileTool, ToolLibraryItem, ToolType } from '../../api/config';
import { ConfirmDialog } from './ConfirmDialog';

interface ProfileToolsFormProps {
  profileId: number;
  onSave?: () => Promise<void>;
  saving?: boolean;
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

export const ProfileToolsForm: React.FC<ProfileToolsFormProps> = ({
  profileId,
  onSave,
}) => {
  // Data state
  const [profileTools, setProfileTools] = useState<ProfileTool[]>([]);
  const [availableTools, setAvailableTools] = useState<ToolLibraryItem[]>([]);
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedToolId, setSelectedToolId] = useState<number | null>(null);
  const [addingTool, setAddingTool] = useState(false);
  
  // Remove confirmation
  const [removingTool, setRemovingTool] = useState<ProfileTool | null>(null);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [tools, library] = await Promise.all([
        configApi.listProfileTools(profileId),
        configApi.listTools(),
      ]);
      
      setProfileTools(tools);
      setAvailableTools(library);
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to load tools';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [profileId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter out tools already assigned to the profile
  const unassignedTools = availableTools.filter(
    (tool) => !profileTools.some((pt) => pt.tool_id === tool.id)
  );

  const handleAddTool = async () => {
    if (!selectedToolId) return;

    try {
      setAddingTool(true);
      await configApi.addToolToProfile(profileId, {
        tool_id: selectedToolId,
        is_enabled: true,
        priority: profileTools.length, // Add at end
      });
      setShowAddDialog(false);
      setSelectedToolId(null);
      await loadData();
      if (onSave) await onSave();
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to add tool';
      setError(message);
    } finally {
      setAddingTool(false);
    }
  };

  const handleToggleTool = async (tool: ProfileTool) => {
    try {
      await configApi.toggleProfileTool(profileId, tool.tool_id);
      await loadData();
      if (onSave) await onSave();
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to toggle tool';
      setError(message);
    }
  };

  const handleRemoveClick = (tool: ProfileTool) => {
    setRemovingTool(tool);
    setRemoveError(null);
  };

  const handleRemoveConfirm = async () => {
    if (!removingTool) return;

    try {
      await configApi.removeToolFromProfile(profileId, removingTool.tool_id);
      setRemovingTool(null);
      await loadData();
      if (onSave) await onSave();
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to remove tool';
      setRemoveError(message);
    }
  };

  const handleMoveUp = async (_tool: ProfileTool, index: number) => {
    if (index === 0) return;
    
    const newOrder = [...profileTools];
    [newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
    
    try {
      await configApi.reorderProfileTools(profileId, {
        tool_ids: newOrder.map(t => t.tool_id),
      });
      await loadData();
    } catch (err) {
      console.error('Failed to reorder:', err);
    }
  };

  const handleMoveDown = async (_tool: ProfileTool, index: number) => {
    if (index === profileTools.length - 1) return;
    
    const newOrder = [...profileTools];
    [newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
    
    try {
      await configApi.reorderProfileTools(profileId, {
        tool_ids: newOrder.map(t => t.tool_id),
      });
      await loadData();
    } catch (err) {
      console.error('Failed to reorder:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-600">Loading tools...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-900">Profile Tools</h3>
          <p className="text-sm text-gray-600">
            Tools assigned to this profile. The agent will have access to all enabled tools.
          </p>
        </div>
        <button
          onClick={() => setShowAddDialog(true)}
          disabled={unassignedTools.length === 0}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Add Tool
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Tools List */}
      {profileTools.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-gray-500 mb-2">No tools assigned to this profile.</p>
          <p className="text-sm text-gray-400 mb-4">
            Add tools from the library to give the agent access to data and capabilities.
          </p>
          {unassignedTools.length > 0 && (
            <button
              onClick={() => setShowAddDialog(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Add Your First Tool
            </button>
          )}
          {unassignedTools.length === 0 && availableTools.length === 0 && (
            <p className="text-sm text-amber-600">
              No tools in the library yet. Create tools in the Tool Library first.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {profileTools.map((tool, index) => (
            <div
              key={tool.id}
              className={`p-4 border rounded-lg transition-colors ${
                tool.is_enabled 
                  ? 'bg-white border-gray-200' 
                  : 'bg-gray-50 border-gray-200 opacity-60'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {/* Reorder buttons */}
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => handleMoveUp(tool, index)}
                      disabled={index === 0}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                      title="Move up"
                    >
                      ▲
                    </button>
                    <button
                      onClick={() => handleMoveDown(tool, index)}
                      disabled={index === profileTools.length - 1}
                      className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                      title="Move down"
                    >
                      ▼
                    </button>
                  </div>

                  {/* Tool info */}
                  <div className="flex items-center">
                    <span className="text-xl mr-3">
                      {TOOL_TYPE_ICONS[tool.tool_type as ToolType]}
                    </span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{tool.tool_name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${TOOL_TYPE_COLORS[tool.tool_type as ToolType]}`}>
                          {TOOL_TYPE_LABELS[tool.tool_type as ToolType]}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">
                        {tool.description_override || tool.tool_description || 'No description'}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3">
                  {/* Enable/Disable Toggle */}
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={tool.is_enabled}
                      onChange={() => handleToggleTool(tool)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    <span className="ml-2 text-sm text-gray-600">
                      {tool.is_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </label>

                  {/* Remove */}
                  <button
                    onClick={() => handleRemoveClick(tool)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Tool Dialog */}
      {showAddDialog && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <div 
              className="fixed inset-0 bg-black bg-opacity-50"
              onClick={() => setShowAddDialog(false)}
            />
            <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Add Tool to Profile</h3>
              
              {unassignedTools.length === 0 ? (
                <p className="text-gray-500">All available tools are already assigned to this profile.</p>
              ) : (
                <>
                  <div className="space-y-2 max-h-80 overflow-y-auto">
                    {unassignedTools.map((tool) => (
                      <label
                        key={tool.id}
                        className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                          selectedToolId === tool.id
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <input
                          type="radio"
                          name="tool"
                          value={tool.id}
                          checked={selectedToolId === tool.id}
                          onChange={() => setSelectedToolId(tool.id)}
                          className="mr-3"
                        />
                        <span className="text-xl mr-3">
                          {TOOL_TYPE_ICONS[tool.tool_type]}
                        </span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{tool.name}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${TOOL_TYPE_COLORS[tool.tool_type]}`}>
                              {TOOL_TYPE_LABELS[tool.tool_type]}
                            </span>
                          </div>
                          <p className="text-sm text-gray-500">
                            {tool.description || 'No description'}
                          </p>
                        </div>
                      </label>
                    ))}
                  </div>

                  <div className="flex justify-end gap-3 mt-6">
                    <button
                      onClick={() => setShowAddDialog(false)}
                      className="px-4 py-2 text-gray-700 hover:text-gray-900"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleAddTool}
                      disabled={!selectedToolId || addingTool}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      {addingTool ? 'Adding...' : 'Add Tool'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Remove Confirmation */}
      <ConfirmDialog
        isOpen={!!removingTool}
        title="Remove Tool"
        message={removingTool ? `Are you sure you want to remove "${removingTool.tool_name}" from this profile?` : ''}
        confirmLabel="Remove"
        onConfirm={handleRemoveConfirm}
        onCancel={() => setRemovingTool(null)}
        error={removeError}
      />
    </div>
  );
};
