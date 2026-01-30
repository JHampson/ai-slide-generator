-- Migration script: Migrate Genie spaces to tool_library and profile_tools
-- Run this AFTER the new tables have been created by init_db()

-- Step 1: Insert existing Genie spaces into tool_library
INSERT INTO tool_library (tool_type, name, description, config, is_active, created_at, updated_at, created_by)
SELECT 
    'genie_space' as tool_type,
    space_name as name,
    description,
    json_build_object('space_id', space_id, 'space_name', space_name) as config,
    true as is_active,
    created_at,
    updated_at,
    'migration' as created_by
FROM config_genie_spaces
ON CONFLICT (name) DO NOTHING;

-- Step 2: Create profile_tools links for each migrated Genie space
INSERT INTO profile_tools (profile_id, tool_id, is_enabled, priority, created_at)
SELECT 
    cgs.profile_id,
    tl.id as tool_id,
    true as is_enabled,
    0 as priority,
    cgs.created_at
FROM config_genie_spaces cgs
JOIN tool_library tl ON tl.config->>'space_id' = cgs.space_id
ON CONFLICT (profile_id, tool_id) DO NOTHING;

-- Verification queries (run manually to check)
-- SELECT COUNT(*) FROM tool_library WHERE tool_type = 'genie_space';
-- SELECT COUNT(*) FROM profile_tools;
-- SELECT p.name as profile, tl.name as tool FROM profile_tools pt 
--   JOIN config_profiles p ON p.id = pt.profile_id 
--   JOIN tool_library tl ON tl.id = pt.tool_id;
