#!/usr/bin/env node
/**
 * Test the API key endpoints
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Load environment
const envPath = join(process.cwd(), '.env.local');
const envContent = readFileSync(envPath, 'utf8');
const envVars = {};
envContent.split('\n').forEach(line => {
  const [key, value] = line.split('=');
  if (key && value) {
    envVars[key] = value;
  }
});

console.log('🔑 Testing API Key Management System');
console.log('=====================================\n');

// Test API key endpoints
async function testEndpoints() {
  const baseUrl = 'http://localhost:3000';
  
  try {
    console.log('📡 Testing API endpoints...');
    
    // Test GET /api/v1/api-keys (should return 401 without auth)
    const response = await fetch(`${baseUrl}/api/v1/api-keys`);
    console.log(`GET /api/v1/api-keys: ${response.status} ${response.statusText}`);
    
    if (response.status === 401) {
      console.log('✅ Endpoints are properly protected with authentication');
    } else {
      console.log('⚠️  Unexpected response - check if server is running');
    }
    
  } catch (error) {
    console.log('❌ Error testing endpoints:', error.message);
    console.log('💡 Make sure to run: npm run dev');
  }
}

console.log('Environment:', envVars.NODE_ENV || 'development');
console.log('Database:', envVars.POSTGRES_URL ? '✅ Configured' : '❌ Missing');
console.log('');

testEndpoints();