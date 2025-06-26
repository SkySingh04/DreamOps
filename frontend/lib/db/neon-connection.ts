import postgres from 'postgres';

interface RetryOptions {
  maxRetries?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
}

const DEFAULT_RETRY_OPTIONS: RetryOptions = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
};

export async function createNeonConnection(
  connectionString: string,
  retryOptions: RetryOptions = DEFAULT_RETRY_OPTIONS
) {
  const { maxRetries, initialDelay, maxDelay, backoffMultiplier } = {
    ...DEFAULT_RETRY_OPTIONS,
    ...retryOptions,
  };

  let lastError: Error | null = null;
  let delay = initialDelay!;

  for (let attempt = 0; attempt <= maxRetries!; attempt++) {
    try {
      console.log(`[Neon] Connection attempt ${attempt + 1}/${maxRetries! + 1}...`);
      
      const sql = postgres(connectionString, {
        // SSL configuration for Neon
        ssl: connectionString.includes('neon.tech') 
          ? { 
              rejectUnauthorized: false,
              // Additional SSL options for compatibility
              minVersion: 'TLSv1.2',
              maxVersion: 'TLSv1.3',
            } 
          : undefined,
        
        // Connection pool settings
        max: 1, // Single connection for serverless
        idle_timeout: 20,
        max_lifetime: 60 * 30, // 30 minutes
        
        // Extended timeouts for Neon cold starts
        connect_timeout: 30,
        
        // Connection options
        connection: {
          application_name: 'dreamops-frontend',
        },
        
        // Transform for proper error handling
        transform: {
          undefined: null,
        },
        
        // Disable prepare to avoid issues with pooled connections
        prepare: false,
        
        // Debug mode for troubleshooting
        debug: process.env.NODE_ENV === 'development' ? console.log : undefined,
        
        // Custom fetch options for better timeout handling
        fetch_types: false,
        
        // Error handler
        onnotice: () => {}, // Suppress notices
      });

      // Test the connection
      const testResult = await sql`SELECT 1 as test, current_timestamp as time`;
      console.log(`[Neon] Connection successful! Server time: ${testResult[0].time}`);
      
      return sql;
    } catch (error: any) {
      lastError = error;
      console.error(`[Neon] Connection attempt ${attempt + 1} failed:`, error.message);
      
      if (attempt < maxRetries!) {
        console.log(`[Neon] Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay = Math.min(delay * backoffMultiplier!, maxDelay!);
      }
    }
  }

  throw new Error(
    `Failed to connect to Neon database after ${maxRetries! + 1} attempts. Last error: ${lastError?.message}`
  );
}

// Helper to test if a connection is alive
export async function testConnection(sql: any): Promise<boolean> {
  try {
    await sql`SELECT 1`;
    return true;
  } catch {
    return false;
  }
}

// Helper to safely close a connection
export async function closeConnection(sql: any): Promise<void> {
  try {
    await sql.end();
  } catch (error) {
    console.error('[Neon] Error closing connection:', error);
  }
}