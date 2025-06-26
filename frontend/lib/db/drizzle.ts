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

// Singleton pattern for database connection
let dbInstance: ReturnType<typeof drizzle> | null = null;
let clientInstance: any = null;
let initializationPromise: Promise<{ db: ReturnType<typeof drizzle>, client: any }> | null = null;

async function initializeDatabase() {
  if (dbInstance) return { db: dbInstance, client: clientInstance };
  
  // For build time placeholder
  if (connectionString.includes('placeholder')) {
    clientInstance = postgres(connectionString, { max: 1 });
    dbInstance = drizzle(clientInstance, { schema });
    return { db: dbInstance, client: clientInstance };
  }
  
  // Initialize the actual database connection
  if (connectionString.includes('neon.tech')) {
    console.log('[Database] Initializing Neon database connection...');
    clientInstance = await createNeonConnection(connectionString);
  } else {
    console.log('[Database] Initializing standard PostgreSQL connection...');
    clientInstance = postgres(connectionString, {
      max: 1,
      idle_timeout: 20,
      connect_timeout: 10,
    });
  }
  
  dbInstance = drizzle(clientInstance, { schema });
  console.log('[Database] Connection initialized successfully');
  
  return { db: dbInstance, client: clientInstance };
}

// Start initialization promise that can be awaited
function startInitialization() {
  if (!initializationPromise && !connectionString.includes('placeholder')) {
    initializationPromise = initializeDatabase().catch(err => {
      console.error('[Database] Failed to initialize:', err);
      // Reset promise so it can be retried
      initializationPromise = null;
      throw err;
    });
  }
  return initializationPromise;
}

// Proxy objects that ensure initialization before use
const createProxy = <T extends object>(getName: () => string) => {
  return new Proxy({} as T, {
    get(target, prop) {
      // Special handling for promise methods - these should not trigger initialization
      if (prop === 'then' || prop === 'catch' || prop === 'finally') {
        return undefined;
      }
      
      // If database is not initialized, start initialization and wait
      if (!dbInstance) {
        // For synchronous contexts, we need to throw an error with instructions
        throw new Error(
          `Database not initialized. The database must be initialized before accessing ${getName()}.${String(prop)}. ` +
          `Use "await ensureDbInitialized()" or "const db = await getDb()" instead of directly accessing the db proxy.`
        );
      }
      
      const instance = getName() === 'db' ? dbInstance : clientInstance;
      const value = Reflect.get(instance, prop);
      if (typeof value === 'function') {
        return value.bind(instance);
      }
      return value;
    },
    has(target, prop) {
      if (!dbInstance) return false;
      const instance = getName() === 'db' ? dbInstance : clientInstance;
      return Reflect.has(instance, prop);
    },
    set(target, prop, value) {
      if (!dbInstance) {
        throw new Error(`Database not initialized. Cannot set ${getName()}.${String(prop)}`);
      }
      const instance = getName() === 'db' ? dbInstance : clientInstance;
      return Reflect.set(instance, prop, value);
    }
  });
};

// Export proxies that will throw if used before initialization
export const db = createProxy<ReturnType<typeof drizzle>>(() => 'db');
export const client = createProxy<any>(() => 'client');

// Helper to ensure database is initialized
export async function ensureDbInitialized() {
  if (!dbInstance) {
    const promise = startInitialization();
    if (promise) {
      await promise;
    } else {
      // Direct initialization for placeholder connections
      await initializeDatabase();
    }
  }
}

// For server components and actions that need immediate database access
export async function getDb() {
  await ensureDbInitialized();
  return dbInstance!;
}

export async function getClient() {
  await ensureDbInitialized();
  return clientInstance!;
}

// Start initialization immediately on module load for server-side
if (typeof window === 'undefined' && !connectionString.includes('placeholder')) {
  startInitialization();
}