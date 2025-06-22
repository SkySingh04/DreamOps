# Custom Domain Setup for dreamops.pointblank.club

## After Connecting GitHub to Amplify:

### Option 1: Via AWS CLI (After GitHub is connected)

```bash
# Create domain association
aws amplify create-domain-association \
  --app-id dwrjpz4zjwnql \
  --domain-name pointblank.club \
  --sub-domain-settings prefix=dreamops,branchName=main \
  --region ap-south-1

# Wait for DNS verification
aws amplify get-domain-association \
  --app-id dwrjpz4zjwnql \
  --domain-name pointblank.club \
  --region ap-south-1
```

### Option 2: Via AWS Console (Easier)

1. Go to: https://ap-south-1.console.aws.amazon.com/amplify/home?region=ap-south-1#/dwrjpz4zjwnql
2. Click on "Domain management" in the left sidebar
3. Click "Add domain"
4. Enter: `pointblank.club`
5. Configure subdomain: `dreamops` → `main` branch
6. Click "Save"

## DNS Records to Add

After adding the domain in Amplify, you'll get DNS records to add to your domain provider:

### Expected DNS Records:

1. **CNAME Record** (for subdomain):
   - Name: `dreamops`
   - Value: `<branch>.<app-id>.amplifyapp.com` (will be provided by Amplify)
   - TTL: 300

2. **Verification Record** (temporary):
   - Type: CNAME
   - Name: `_<verification-id>.dreamops`
   - Value: `_<verification-value>.acm-validations.aws`
   - TTL: 300

## Where to Add DNS Records:

### If using Cloudflare:
1. Log in to Cloudflare
2. Select `pointblank.club` domain
3. Go to DNS settings
4. Add CNAME record for `dreamops`
5. Set Proxy status to "DNS only" (gray cloud)

### If using other DNS providers:
1. Log in to your DNS provider
2. Find DNS management for `pointblank.club`
3. Add the CNAME records provided by Amplify

## Verification Process:

1. After adding DNS records, Amplify will verify ownership (takes 5-30 minutes)
2. Once verified, SSL certificate will be provisioned automatically
3. Your site will be available at: https://dreamops.pointblank.club

## Check Domain Status:

```bash
# Check domain association status
aws amplify get-domain-association \
  --app-id dwrjpz4zjwnql \
  --domain-name pointblank.club \
  --region ap-south-1 \
  --query 'domainAssociation.domainStatus'
```

Status progression:
- `CREATING` → `REQUESTING_CERTIFICATE` → `PENDING_VERIFICATION` → `PENDING_DEPLOYMENT` → `AVAILABLE`

## Troubleshooting:

1. **Domain not verifying**: Check DNS propagation with `dig dreamops.pointblank.club`
2. **SSL issues**: Wait for certificate provisioning (up to 48 hours)
3. **404 errors**: Ensure GitHub is connected and deployment succeeded

## Alternative: Full Domain Setup

If you want to use the root domain `dreamops.pointblank.club` directly:

```bash
aws amplify create-domain-association \
  --app-id dwrjpz4zjwnql \
  --domain-name dreamops.pointblank.club \
  --sub-domain-settings prefix=,branchName=main prefix=www,branchName=main \
  --region ap-south-1
```

This would require:
- A record for root domain
- CNAME for www subdomain