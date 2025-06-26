import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';
import dotenv from 'dotenv';

dotenv.config();

// Ensure POSTGRES_URL is available, use a placeholder during build if needed
const connectionString = process.env.POSTGRES_URL || 'postgresql://placeholder:placeholder@localhost:5432/placeholder';

// Create client with the connection string
const client = postgres(connectionString, {
  // Prevent actual connection during build time
  connect_timeout: process.env.NODE_ENV === 'production' && !process.env.POSTGRES_URL?.includes('neon.tech') ? 1 : undefined,
  max: 1, // Limit connections
});

const db = drizzle(client, { schema });

export { client, db };
