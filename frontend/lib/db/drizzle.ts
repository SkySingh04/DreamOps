import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import dotenv from 'dotenv';

dotenv.config();

// Mock database for static export
const createMockClient = () => {
  return new Proxy({} as postgres.Sql, {
    get() {
      return () => Promise.resolve([]);
    }
  });
};

// Create a mock database for static export builds
const connectionString = 'postgresql://mock:mock@localhost:5432/mock';
const client = createMockClient();
const db = drizzle(client, { schema });

export { client, db };
