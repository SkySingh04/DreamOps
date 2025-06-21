# Oncall AI Agent - Frontend

Modern web interface for the Oncall AI Agent, built with Next.js 15 and Tailwind CSS.

## Features

- 📊 **Real-time Dashboard**: Monitor active incidents and system health
- 🚨 **Incident Management**: View and analyze incident history
- 🔌 **Integration Status**: Monitor MCP integration connections
- ⚙️ **Settings Management**: Configure AI agent and alert preferences
- 🔐 **Authentication**: Built-in user management with role-based access

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Database**: PostgreSQL with Drizzle ORM
- **Authentication**: Custom JWT-based auth
- **State Management**: React hooks + SWR

## Prerequisites

- Node.js 20+
- PostgreSQL database
- Backend API running on port 8000

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env.local
   ```

3. Configure your `.env.local`:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/oncall_agent
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Set up the database:
   ```bash
   npm run db:setup
   npm run db:migrate
   npm run db:seed  # Optional: adds sample data
   ```

5. Run the development server:
   ```bash
   npm run dev
   ```

Visit http://localhost:3000

## Default Credentials

For development, the seed script creates:
- Email: `test@test.com`
- Password: `admin123`

## Project Structure

```
frontend/
├── app/               # Next.js app router pages
│   ├── (dashboard)/  # Authenticated dashboard pages
│   ├── (login)/      # Authentication pages
│   └── api/          # API routes
├── components/       # Reusable React components
├── lib/             # Utilities and configurations
│   ├── db/          # Database schema and queries
│   ├── auth/        # Authentication helpers
│   └── payments/    # Stripe integration (future)
└── public/          # Static assets
```

## Key Pages

- `/dashboard` - Main metrics and recent incidents
- `/incidents` - Full incident history with AI analysis
- `/integrations` - MCP integration management
- `/settings` - Agent configuration and API keys

## Development

### Adding a New Page

1. Create a new directory in `app/(dashboard)/`
2. Add a `page.tsx` file
3. Update navigation in `app/(dashboard)/dashboard/layout.tsx`

### Styling

We use Tailwind CSS with shadcn/ui components. To add a new component:

```bash
npx shadcn-ui@latest add [component-name]
```

### API Integration

The frontend expects the backend API to be available at `NEXT_PUBLIC_API_URL`. 
Future endpoints to implement:

- `GET /api/alerts` - Fetch recent alerts
- `GET /api/incidents` - Incident history
- `GET /api/integrations` - Integration status
- `POST /api/settings` - Update configuration

## Building for Production

```bash
npm run build
npm start
```

Or use Docker:

```bash
docker build -t oncall-frontend .
docker run -p 3000:3000 oncall-frontend
```

## Environment Variables

See `.env.example` for all required environment variables.

## Contributing

1. Follow the existing code style
2. Use TypeScript for new components
3. Add appropriate error handling
4. Update this README for significant changes

## License

Same as the main project