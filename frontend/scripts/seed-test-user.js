import postgres from 'postgres';
import dotenv from 'dotenv';
import bcrypt from 'bcryptjs';

// Load environment variables
dotenv.config({ path: '.env.local' });

const sql = postgres(process.env.POSTGRES_URL);

async function seedTestUser() {
  try {
    console.log('Creating test user and team...\n');
    
    // Hash the password
    const passwordHash = await bcrypt.hash('AdminPass123!', 10);
    
    // Create a test team
    const [team] = await sql`
      INSERT INTO teams (name, subscription_status)
      VALUES ('Test Team', 'trial')
      RETURNING id, name
    `;
    console.log(`✓ Created team: ${team.name} (ID: ${team.id})`);
    
    // Create the test user
    const [user] = await sql`
      INSERT INTO users (name, email, password_hash, role, is_setup_complete)
      VALUES ('Admin User', 'admin@oncall.ai', ${passwordHash}, 'owner', false)
      RETURNING id, email
    `;
    console.log(`✓ Created user: ${user.email} (ID: ${user.id})`);
    
    // Add user to team
    await sql`
      INSERT INTO team_members (user_id, team_id, role)
      VALUES (${user.id}, ${team.id}, 'owner')
    `;
    console.log(`✓ Added user to team`);
    
    // Initialize setup requirements for the user
    const requirements = [
      { type: 'llm_config', required: true },
      { type: 'pagerduty', required: true },
      { type: 'kubernetes', required: true },
      { type: 'github', required: false },
      { type: 'notion', required: false },
      { type: 'grafana', required: false }
    ];
    
    for (const req of requirements) {
      await sql`
        INSERT INTO user_setup_requirements (user_id, requirement_type, is_required, is_completed)
        VALUES (${user.id}, ${req.type}, ${req.required}, false)
      `;
    }
    console.log(`✓ Created setup requirements`);
    
    console.log('\n✅ Test user created successfully!');
    console.log('Email: admin@oncall.ai');
    console.log('Password: AdminPass123!');
    
  } catch (error) {
    console.error('Error seeding test user:', error);
    
    // Check if user already exists
    if (error.code === '23505') {
      console.log('\n⚠️  User already exists');
    }
  } finally {
    await sql.end();
  }
}

seedTestUser();