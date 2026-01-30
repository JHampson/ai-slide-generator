/**
 * Tool Library Page - App-level tool management.
 * 
 * Allows administrators to create and manage tools that can be
 * assigned to multiple profiles.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { configApi, ConfigApiError } from '../../api/config';
import type { ToolLibraryItem, ToolType } from '../../api/config';
import { ToolLibraryList } from './ToolLibraryList';
import { ToolLibraryForm } from './ToolLibraryForm';
import { ConfirmDialog } from './ConfirmDialog';

interface ToolLibraryPageProps {
  onClose?: () => void;
}

export const ToolLibraryPage: React.FC<ToolLibraryPageProps> = ({ onClose }) => {
  const [tools, setTools] = useState<ToolLibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<ToolType | ''>('');
  
  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingTool, setEditingTool] = useState<ToolLibraryItem | null>(null);
  
  // Delete confirmation
  const [deletingTool, setDeletingTool] = useState<ToolLibraryItem | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const loadTools = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await configApi.listTools(filterType || undefined);
      setTools(data);
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to load tools';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    loadTools();
  }, [loadTools]);

  const handleCreate = () => {
    setEditingTool(null);
    setShowForm(true);
  };

  const handleEdit = (tool: ToolLibraryItem) => {
    setEditingTool(tool);
    setShowForm(true);
  };

  const handleFormClose = () => {
    setShowForm(false);
    setEditingTool(null);
  };

  const handleFormSave = async () => {
    setShowForm(false);
    setEditingTool(null);
    await loadTools();
  };

  const handleDeleteClick = (tool: ToolLibraryItem) => {
    setDeletingTool(tool);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!deletingTool) return;
    
    try {
      await configApi.deleteTool(deletingTool.id);
      setDeletingTool(null);
      await loadTools();
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to delete tool';
      setDeleteError(message);
    }
  };

  const handleDeleteCancel = () => {
    setDeletingTool(null);
    setDeleteError(null);
  };

  const toolTypes: { value: ToolType | ''; label: string }[] = [
    { value: '', label: 'All Types' },
    { value: 'genie_space', label: 'Genie Space' },
    { value: 'vector_index', label: 'Vector Index' },
    { value: 'mcp_server', label: 'MCP Server' },
    { value: 'uc_function', label: 'UC Function' },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tool Library</h1>
          <p className="text-sm text-gray-600 mt-1">
            Manage tools that can be assigned to profiles. Tools defined here are available across all profiles.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-900"
            >
              Close
            </button>
          )}
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Add Tool
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="mb-4">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as ToolType | '')}
          className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          {toolTypes.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-gray-600">Loading tools...</div>
        </div>
      )}

      {/* List */}
      {!loading && (
        <ToolLibraryList
          tools={tools}
          onEdit={handleEdit}
          onDelete={handleDeleteClick}
        />
      )}

      {/* Create/Edit Form Modal */}
      {showForm && (
        <ToolLibraryForm
          tool={editingTool}
          onSave={handleFormSave}
          onClose={handleFormClose}
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deletingTool}
        title="Delete Tool"
        message={deletingTool ? `Are you sure you want to delete "${deletingTool.name}"? This will remove it from all profiles that use it.` : ''}
        confirmLabel="Delete"
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        error={deleteError}
      />
    </div>
  );
};
