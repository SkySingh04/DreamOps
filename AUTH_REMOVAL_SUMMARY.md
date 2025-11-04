# Authentication Removal Summary

## Overview
All authentication has been removed from the DreamOps codebase. Authentication is now handled exclusively by Authentik reverse proxy.

## Files Removed

### Backend
- `backend/src/oncall_agent/api/routers/firebase_auth.py` - Firebase authentication router
- `backend/src/oncall_agent/api/routers/auth.py` - Basic authentication router
- `backend/src/oncall_agent/api/routers/auth_setup.py` - Authentication setup router
- `backend/src/oncall_agent/api/auth.py` - Authentication utilities
- `backend/src/oncall_agent/api/models/auth.py` - Authentication models
- `backend/src/oncall_agent/security/firebase_auth.py` - Firebase security module

### Frontend
- `frontend/app/(login)/` - Entire login pages directory
- `frontend/app/auth/` - Entire auth flow directory (signin, signup, complete-setup)
- `frontend/lib/firebase/` - Firebase configuration and auth context
- `frontend/lib/api/auth.ts` - Authentication API client

## Files Modified

### Backend
- `backend/api_server.py` - Removed auth router imports and middleware
- `backend/src/oncall_agent/api/routers/chaos.py` - Removed FirebaseUser dependency
- `backend/pyproject.toml` - Removed firebase-admin, pyjwt, and bcrypt dependencies

### Frontend
- `frontend/lib/providers.tsx` - Removed AuthProvider
- `frontend/lib/db/queries.ts` - Replaced auth functions with stubs
- `frontend/app/api/logout/route.ts` - Simplified to just return success
- `frontend/app/api/user/route.ts` - Removed Firebase token checking
- `frontend/package.json` - Removed firebase and jose dependencies

### Documentation
- `README.md` - Added Authentik authentication note
- `CLAUDE.md` - Updated architecture decisions to reflect Authentik auth

## Dependencies Removed

### Backend (pyproject.toml)
- `firebase-admin>=6.9.0`
- `pyjwt>=2.10.1`
- `bcrypt>=4.3.0`

### Frontend (package.json)
- `firebase: ^11.9.1`
- `jose: ^6.0.11`

## Authentication Flow (New)

Authentication is now handled entirely by Authentik reverse proxy:

1. **User Access**: Users access the application through Authentik
2. **Authentik Validation**: Authentik validates credentials
3. **Header Injection**: Authentik injects user identity headers
4. **Application Access**: Application reads user info from headers

## Required Headers from Authentik

The application expects Authentik to provide user identity via headers:
- `X-Authentik-Username` - Username
- `X-Authentik-Email` - User email
- `X-Authentik-Groups` - User groups/roles (optional)

## Next Steps for Integration

To integrate with Authentik:

1. **Configure Authentik** to proxy requests to the DreamOps application
2. **Set up headers** to pass user identity information
3. **Update application code** (if needed) to read user info from Authentik headers
4. **Configure CORS** to allow requests from Authentik

## Notes

- All existing database tables remain unchanged
- User management is now handled by Authentik
- No login/signup flows in the application
- No token validation in the application
- No session management in the application

## Testing

To test the application without Authentik during development:
1. Mock the Authentik headers in your development environment
2. Use a tool like nginx or a simple proxy to inject test headers
3. Or temporarily add middleware to inject test user headers in development mode

---

Generated: 2025-11-04
