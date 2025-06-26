import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import dotenv from 'dotenv';
import { createNeonConnection } from './neon-connection';

dotenv.config();

// Get the appropriate database URL based on environment
const getDatabaseUrl = () => {
  const env = process.env.NODE_ENV || 'development';
  
  // For Vercel/production deployments
  if (process.env.POSTGRES_URL) {
    return process.env.POSTGRES_URL;
  }
  
  // For local development
  if (env === 'development') {
    return process.env.DATABASE_URL || process.env.POSTGRES_URL || 'postgresql://placeholder:placeholder@localhost:5432/placeholder';
  }
  
  // Fallback for build time
  return 'postgresql://placeholder:placeholder@localhost:5432/placeholder';
};

const connectionString = getDatabaseUrl();

// Create client based on whether it's Neon or not
let client: any;

if (connectionString.includes('neon.tech')) {
  // Use async initialization for Neon with retry logic
  console.log('[Database] Detected Neon database, using enhanced connection handling...');
  
  // For build time, use a placeholder
  if (connectionString.includes('placeholder')) {
    client = postgres(connectionString, { max: 1 });
  } else {
    // This will be initialized asynchronously
    client = null;
    
    // Initialize on first use
    const initPromise = createNeonConnection(connectionString).then(sql => {
      client = sql;
      return sql;
    });
    
    // Proxy to handle async initialization
    const clientProxy = new Proxy({}, {
      get(target, prop) {
        if (!client) {
          throw new Error('Database not initialized. Please await db initialization first.');
        }
        return client[prop];
      }
    });
    
    client = clientProxy;
    
    // Export the initialization promise
    (global as any).__dbInitPromise = initPromise;
  }
} else {
  // Standard postgres connection for non-Neon databases
  client = postgres(connectionString, {
    max: 1,
    idle_timeout: 20,
    connect_timeout: 10,
  });
}

const db = drizzle(client, { schema });

// Helper to ensure database is initialized (for Neon)
export async function ensureDbInitialized() {
  if ((global as any).__dbInitPromise) {
    await (global as any).__dbInitPromise;
  }
}

export { client, db };