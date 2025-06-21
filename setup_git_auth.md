# Safe GitHub Authentication Setup

## Recommended Method: Personal Access Token with Credential Storage

### Step 1: Create a GitHub Personal Access Token

1. Go to GitHub.com → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "oncall-agent-push"
4. Select scopes:
   - ✅ repo (all)
   - ✅ workflow (if you have GitHub Actions)
5. Click "Generate token"
6. **COPY THE TOKEN NOW** (you won't see it again!)

### Step 2: Configure Git to Store Credentials Safely

Run these commands in your terminal:

```bash
# Configure git to store credentials securely
git config --global credential.helper store

# Set your GitHub username
git config --global user.name "SkySingh04"
git config --global user.email "your-email@example.com"
```

### Step 3: Push with Token Authentication

When you run:
```bash
git push origin main
```

You'll be prompted for:
- Username: `SkySingh04`
- Password: **Paste your Personal Access Token here** (not your GitHub password!)

Git will securely save these credentials so you won't need to enter them again.

### Alternative: One-Time Push (Less Secure)

If you just want to push once without saving credentials:

```bash
git push https://SkySingh04:YOUR_TOKEN_HERE@github.com/SkySingh04/oncall-agent.git main
```

Replace `YOUR_TOKEN_HERE` with your actual token.

## Why This is Safe:

1. **Token-based**: More secure than passwords
2. **Limited scope**: Token only has permissions you granted
3. **Revocable**: Can delete token anytime from GitHub
4. **Stored securely**: Git credential helper encrypts storage

## After Setup:

Your future pushes will work with just:
```bash
git push
```

No authentication needed!