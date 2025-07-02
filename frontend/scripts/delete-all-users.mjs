import postgres from 'postgres';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: join(__dirname, '../.env') });

async function deleteAllUsers() {
  const connectionString = process.env.POSTGRES_URL || process.env.DATABASE_URL;
  
  if (!connectionString) {
    console.error('❌ POSTGRES_URL or DATABASE_URL not found in environment variables');
    process.exit(1);
  }
  
  console.log('🗑️  Starting to delete all users and related data...\n');
  
  const sql = postgres(connectionString, {
    ssl: 'require',
    max: 1,
  });
  
  try {
    // Get current counts
    const userCount = await sql`SELECT COUNT(*) as count FROM users`;
    const incidentCount = await sql`SELECT COUNT(*) as count FROM incidents`;
    const apiKeyCount = await sql`SELECT COUNT(*) as count FROM api_keys`;
    const teamCount = await sql`SELECT COUNT(*) as count FROM teams`;
    
    console.log('Current data:');
    console.log(`  - Users: ${userCount[0].count}`);
    console.log(`  - Teams: ${teamCount[0].count}`);
    console.log(`  - Incidents: ${incidentCount[0].count}`);
    console.log(`  - API Keys: ${apiKeyCount[0].count}`);
    console.log('');
    
    // Delete in order to respect foreign key constraints
    console.log('Deleting related data...');
    
    // Delete setup validation logs
    const deletedSetupLogs = await sql`DELETE FROM setup_validation_logs RETURNING id`;
    console.log(`✓ Deleted ${deletedSetupLogs.length} setup validation logs`);
    
    // Delete incident logs
    const deletedIncidentLogs = await sql`DELETE FROM incident_logs RETURNING id`;
    console.log(`✓ Deleted ${deletedIncidentLogs.length} incident logs`);
    
    // Delete incidents
    const deletedIncidents = await sql`DELETE FROM incidents RETURNING id`;
    console.log(`✓ Deleted ${deletedIncidents.length} incidents`);
    
    // Delete API keys
    const deletedApiKeys = await sql`DELETE FROM api_keys RETURNING id`;
    console.log(`✓ Deleted ${deletedApiKeys.length} API keys`);
    
    // Delete team integrations
    const deletedTeamIntegrations = await sql`DELETE FROM team_integrations RETURNING id`;
    console.log(`✓ Deleted ${deletedTeamIntegrations.length} team integrations`);
    
    // Delete integration audit logs
    const deletedIntegrationLogs = await sql`DELETE FROM integration_audit_logs RETURNING id`;
    console.log(`✓ Deleted ${deletedIntegrationLogs.length} integration audit logs`);
    
    // Delete metrics
    const deletedMetrics = await sql`DELETE FROM metrics RETURNING id`;
    console.log(`✓ Deleted ${deletedMetrics.length} metrics`);
    
    // Delete ai_actions
    const deletedAiActions = await sql`DELETE FROM ai_actions RETURNING id`;
    console.log(`✓ Deleted ${deletedAiActions.length} AI actions`);
    
    // Delete activity logs
    const deletedLogs = await sql`DELETE FROM activity_logs RETURNING id`;
    console.log(`✓ Deleted ${deletedLogs.length} activity logs`);
    
    // Delete user setup requirements
    const deletedSetupReqs = await sql`DELETE FROM user_setup_requirements RETURNING id`;
    console.log(`✓ Deleted ${deletedSetupReqs.length} user setup requirements`);
    
    // Delete invitations
    const deletedInvitations = await sql`DELETE FROM invitations RETURNING id`;
    console.log(`✓ Deleted ${deletedInvitations.length} invitations`);
    
    // Delete team members
    const deletedTeamMembers = await sql`DELETE FROM team_members RETURNING id`;
    console.log(`✓ Deleted ${deletedTeamMembers.length} team members`);
    
    // Delete teams
    const deletedTeams = await sql`DELETE FROM teams RETURNING id`;
    console.log(`✓ Deleted ${deletedTeams.length} teams`);
    
    // Finally, delete all users
    const deletedUsers = await sql`DELETE FROM users RETURNING id`;
    console.log(`✓ Deleted ${deletedUsers.length} users`);
    
    console.log('\n✅ Successfully deleted all users and related data!');
    
  } catch (error) {
    console.error('❌ Error deleting users:', error);
    process.exit(1);
  } finally {
    await sql.end();
  }
  
  process.exit(0);
}

// Add confirmation prompt
console.log('⚠️  WARNING: This will delete ALL users and their related data!');
console.log('This action cannot be undone.\n');
console.log('Environment: ' + ((process.env.POSTGRES_URL || process.env.DATABASE_URL)?.includes('prod') ? 'PRODUCTION' : 'LOCAL/STAGING'));
console.log('\nPress Ctrl+C to cancel, or wait 5 seconds to continue...\n');

setTimeout(() => {
  deleteAllUsers();
}, 5000);