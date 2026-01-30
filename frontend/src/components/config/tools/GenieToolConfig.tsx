/**
 * Genie Tool Configuration Form.
 * 
 * Allows selecting a Databricks Genie space and configuring
 * how it should be used by the agent.
 */

import React, { useState } from 'react';
import { configApi, ConfigApiError } from '../../../api/config';
import type { AvailableGenieSpaces } from '../../../api/config';

interface GenieToolConfigProps {
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export const GenieToolConfig: React.FC<GenieToolConfigProps> = ({
  config,
  onChange,
}) => {
  const [availableSpaces, setAvailableSpaces] = useState<AvailableGenieSpaces | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manualSpaceId, setManualSpaceId] = useState('');
  const [lookingUp, setLookingUp] = useState(false);

  const spaceId = (config.space_id as string) || '';
  const spaceName = (config.space_name as string) || '';

  const loadSpaces = async () => {
    if (availableSpaces) return;
    
    try {
      setLoading(true);
      setError(null);
      const spaces = await configApi.discoverGenieSpaces();
      setAvailableSpaces(spaces);
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Failed to load Genie spaces';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleSpaceSelect = (selectedSpaceId: string) => {
    const spaceDetails = availableSpaces?.spaces[selectedSpaceId];
    onChange({
      ...config,
      space_id: selectedSpaceId,
      space_name: spaceDetails?.title || selectedSpaceId,
    });
  };

  const handleManualLookup = async () => {
    if (!manualSpaceId.trim()) return;

    try {
      setLookingUp(true);
      setError(null);
      const result = await configApi.lookupGenieSpace(manualSpaceId.trim());
      onChange({
        ...config,
        space_id: result.space_id,
        space_name: result.title,
      });
      setManualSpaceId('');
    } catch (err) {
      const message = err instanceof ConfigApiError 
        ? err.message 
        : 'Space not found';
      setError(message);
    } finally {
      setLookingUp(false);
    }
  };

  // Filter and sort spaces for dropdown
  const sortedSpaces = availableSpaces
    ? Object.entries(availableSpaces.spaces)
        .sort(([, a], [, b]) => a.title.localeCompare(b.title))
    : [];

  return (
    <div className="space-y-4">
      {/* Current Selection */}
      {spaceId && (
        <div className="p-3 bg-green-50 border border-green-200 rounded-md">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-800">Selected Space</p>
              <p className="text-sm text-green-700">{spaceName || spaceId}</p>
              <p className="text-xs text-green-600 font-mono">{spaceId}</p>
            </div>
            <button
              type="button"
              onClick={() => onChange({ ...config, space_id: '', space_name: '' })}
              className="text-green-600 hover:text-green-800"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Space Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Genie Space <span className="text-red-500">*</span>
        </label>
        <div className="flex gap-2">
          <select
            value={spaceId}
            onChange={(e) => handleSpaceSelect(e.target.value)}
            onFocus={loadSpaces}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">Select a Genie space...</option>
            {loading && <option disabled>Loading spaces...</option>}
            {sortedSpaces.map(([id, details]) => (
              <option key={id} value={id}>
                {details.title}
              </option>
            ))}
          </select>
        </div>
        {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
      </div>

      {/* Manual Space ID Entry */}
      <div className="border-t pt-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Or enter Space ID manually
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={manualSpaceId}
            onChange={(e) => setManualSpaceId(e.target.value)}
            placeholder="Paste Genie space ID here..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            type="button"
            onClick={handleManualLookup}
            disabled={lookingUp || !manualSpaceId.trim()}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
          >
            {lookingUp ? 'Looking up...' : 'Lookup'}
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          You can find the space ID in the Genie space URL or settings.
        </p>
      </div>
    </div>
  );
};
