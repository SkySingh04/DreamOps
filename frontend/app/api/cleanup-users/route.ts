import { NextResponse } from 'next/server';
import { getDb } from '@/lib/db/drizzle';
import { users, userApiKeys, userSetupRequirements, setupValidationLogs, activityLogs, incidents, incidentLogs, aiActions, integrations } from '@/lib/db/schema';

export async function DELETE() {
  const deletedTables: string[] = [];
  const errors: string[] = [];
  
  try {
    const db = await getDb();
    
    console.log('Starting cleanup of all user data...');
    
    // Helper function to safely delete from a table
    const safeDelete = async (tableName: string, table: any) => {
      try {
        await db.delete(table);
        deletedTables.push(tableName);
        console.log(`✓ Deleted ${tableName}`);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        if (errorMessage.includes('does not exist')) {
          console.log(`- Table ${tableName} does not exist, skipping...`);
        } else {
          errors.push(`${tableName}: ${errorMessage}`);
          console.error(`✗ Error deleting ${tableName}:`, errorMessage);
        }
      }
    };
    
    // Delete in order of dependencies
    await safeDelete('setup_validation_logs', setupValidationLogs);
    await safeDelete('user_setup_requirements', userSetupRequirements);
    await safeDelete('user_api_keys', userApiKeys);
    await safeDelete('ai_actions', aiActions);
    await safeDelete('incident_logs', incidentLogs);
    await safeDelete('incidents', incidents);
    await safeDelete('integrations', integrations);
    await safeDelete('activity_logs', activityLogs);
    await safeDelete('users', users);
    
    return NextResponse.json({ 
      success: errors.length === 0, 
      message: errors.length === 0 
        ? 'Successfully deleted all user data from the database' 
        : 'Cleanup completed with some errors',
      deletedTables,
      errors
    });
    
  } catch (error) {
    console.error('Error cleaning up users:', error);
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error',
      deletedTables,
      errors
    }, { status: 500 });
  }
}