# CI/CD Guide

This guide covers the continuous integration and deployment pipeline for DreamOps, including GitHub Actions workflows, security scanning, and deployment automation.

## Overview

DreamOps uses GitHub Actions for:
- **Automated Testing**: Unit, integration, and end-to-end tests
- **Security Scanning**: Dependency vulnerability checks and SAST
- **Code Quality**: Linting, formatting, and type checking
- **Deployment**: Automated deployment to staging and production
- **Documentation**: Markdown file validation and organization

## GitHub Actions Workflows

### Workflow Structure

The CI/CD pipeline consists of several specialized workflows:

```
.github/workflows/
├── check-markdown-files.yml     # Documentation governance
├── backend-ci.yml               # Backend testing and deployment
├── frontend-ci.yml              # Frontend testing and deployment
├── security-scan.yml            # Security vulnerability scanning
└── integration-tests.yml        # Cross-service integration tests
```

## Documentation Governance

### Markdown File Validation

The `check-markdown-files.yml` workflow enforces documentation organization by:

1. **Allowed Locations**: Only permits `.md` files in specific locations
2. **Centralized Documentation**: Encourages use of the `/docs` folder
3. **Prevents Sprawl**: Blocks random markdown files across the repository

#### Allowed Markdown Files

- `./README.md` - Main project documentation
- `./CLAUDE.md` - AI assistant instructions
- `./docs/*.md` - Organized documentation files

#### Workflow Configuration

```yaml
name: Check Markdown Files

on:
  pull_request:
    paths:
      - '**/*.md'
  push:
    branches: [main]
    paths:
      - '**/*.md'

jobs:
  check-markdown-files:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check for unauthorized markdown files
        run: |
          # Find all .md files
          ALL_MD_FILES=$(find . -name "*.md" -not -path "./.git/*" | sort)
          
          # Define allowed files
          ALLOWED_FILES=$(cat << 'EOF'
          ./README.md
          ./CLAUDE.md
          ./docs/database-setup.md
          ./docs/deployment.md
          ./docs/mcp-integrations.md
          ./docs/pagerduty-integration.md
          ./docs/yolo-mode.md
          ./docs/technical-details.md
          ./docs/ci-cd.md
          EOF
          )
          
          # Check for unauthorized files
          UNAUTHORIZED=""
          for file in $ALL_MD_FILES; do
            if ! echo "$ALLOWED_FILES" | grep -q "^$file$"; then
              UNAUTHORIZED="$UNAUTHORIZED$file\n"
            fi
          done
          
          if [ -n "$UNAUTHORIZED" ]; then
            echo "❌ Unauthorized markdown files found:"
            echo -e "$UNAUTHORIZED"
            echo ""
            echo "📝 Please consolidate your documentation into one of these approved files:"
            echo "   • ./README.md - Main project documentation"
            echo "   • ./CLAUDE.md - AI assistant instructions" 
            echo "   • ./docs/*.md - Organized documentation files"
            echo ""
            echo "🎯 This keeps our documentation organized and prevents sprawl!"
            exit 1
          fi
          
          echo "✅ All markdown files are in approved locations!"
```

### Benefits

1. **Organized Documentation**: All docs are centralized in `/docs`
2. **Prevents Duplication**: Stops scattered documentation files
3. **Quality Control**: Ensures documentation follows project standards
4. **Easy Maintenance**: Centralized location makes updates easier

## Backend CI/CD

### Backend Workflow (`backend-ci.yml`)

The backend pipeline includes:

#### Testing Phase
```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install uv
        uv sync
    
    - name: Run tests
      run: |
        cd backend
        uv run pytest tests/ -v
    
    - name: Run linting
      run: |
        cd backend
        uv run ruff check .
        uv run mypy .
```

#### Security Scanning
```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Run Bandit security scan
      run: |
        cd backend
        pip install bandit
        bandit -r src/ -f json -o bandit-results.json
    
    - name: Upload security scan results
      uses: actions/upload-artifact@v3
      with:
        name: bandit-results
        path: backend/bandit-results.json
```

#### Docker Build and Push
```yaml
build:
  needs: [test, security]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Login to Amazon ECR
      run: aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    - name: Build and push Docker image
      run: |
        cd backend
        docker build -t $ECR_REGISTRY/dreamops-backend:$GITHUB_SHA -f Dockerfile.prod .
        docker push $ECR_REGISTRY/dreamops-backend:$GITHUB_SHA
```

#### Deployment
```yaml
deploy:
  needs: build
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
  steps:
    - name: Deploy to ECS
      run: |
        aws ecs update-service \
          --cluster dreamops-cluster \
          --service dreamops-backend \
          --force-new-deployment
```

## Frontend CI/CD

### Frontend Workflow (`frontend-ci.yml`)

#### Testing and Building
```yaml
test-and-build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    
    - name: Install dependencies
      run: |
        cd frontend
        npm ci
    
    - name: Run tests
      run: |
        cd frontend
        npm test
    
    - name: Run type checking
      run: |
        cd frontend
        npm run type-check
    
    - name: Build application
      run: |
        cd frontend
        npm run build
      env:
        NEXT_PUBLIC_API_URL: ${{ secrets.NEXT_PUBLIC_API_URL }}
```

#### Database Migration
```yaml
migrate:
  runs-on: ubuntu-latest
  steps:
    - name: Run database migrations
      run: |
        cd frontend
        npm run db:migrate:production
      env:
        POSTGRES_URL: ${{ secrets.POSTGRES_URL_PROD }}
```

#### Deployment Options

**Option 1: AWS Amplify**
```yaml
deploy-amplify:
  needs: [test-and-build, migrate]
  runs-on: ubuntu-latest
  steps:
    - name: Trigger Amplify deployment
      run: |
        aws amplify start-job \
          --app-id ${{ secrets.AMPLIFY_APP_ID }} \
          --branch-name main \
          --job-type RELEASE
```

**Option 2: S3 + CloudFront**
```yaml
deploy-s3:
  needs: [test-and-build, migrate]
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to S3
      run: |
        cd frontend
        aws s3 sync .next/ s3://${{ secrets.S3_BUCKET }}
    
    - name: Invalidate CloudFront
      run: |
        aws cloudfront create-invalidation \
          --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
          --paths "/*"
```

## Security Scanning

### Vulnerability Scanning Workflow

```yaml
name: Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Weekly on Monday

jobs:
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run dependency vulnerability scan
        uses: github/super-linter@v4
        env:
          DEFAULT_BRANCH: main
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Backend dependency check
        run: |
          cd backend
          pip install safety
          safety check
      
      - name: Frontend dependency check
        run: |
          cd frontend
          npm audit --audit-level high
  
  sast-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run CodeQL analysis
        uses: github/codeql-action/init@v2
        with:
          languages: python, javascript
      
      - name: Perform CodeQL analysis
        uses: github/codeql-action/analyze@v2
```

### Secret Scanning

GitHub automatically scans for exposed secrets. Additionally:

```yaml
secret-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Run TruffleHog
      uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        base: main
        head: HEAD
```

## Integration Testing

### Cross-Service Integration Tests

```yaml
name: Integration Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  integration-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup test environment
        run: |
          docker-compose -f tests/docker-compose.test.yml up -d
      
      - name: Wait for services
        run: |
          timeout 300 bash -c 'until curl -f http://localhost:8000/health; do sleep 5; done'
      
      - name: Run integration tests
        run: |
          cd backend
          uv run pytest tests/test_integration.py -v
      
      - name: Cleanup
        run: |
          docker-compose -f tests/docker-compose.test.yml down
```

## Deployment Strategies

### Environment-Specific Deployments

#### Staging Deployment
```yaml
deploy-staging:
  if: github.ref == 'refs/heads/develop'
  environment: staging
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to staging
      run: |
        # Deploy to staging environment
        aws ecs update-service \
          --cluster dreamops-staging \
          --service dreamops-backend-staging \
          --force-new-deployment
```

#### Production Deployment
```yaml
deploy-production:
  if: github.ref == 'refs/heads/main'
  environment: production
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to production
      run: |
        # Deploy to production environment
        aws ecs update-service \
          --cluster dreamops-production \
          --service dreamops-backend-production \
          --force-new-deployment
```

### Blue-Green Deployment

```yaml
blue-green-deploy:
  runs-on: ubuntu-latest
  steps:
    - name: Deploy to green environment
      run: |
        # Deploy new version to green environment
        aws ecs create-service \
          --cluster dreamops-cluster \
          --service-name dreamops-backend-green \
          --task-definition dreamops-backend:$GITHUB_SHA
    
    - name: Health check green environment
      run: |
        timeout 300 bash -c 'until curl -f http://green.dreamops.com/health; do sleep 10; done'
    
    - name: Switch traffic to green
      run: |
        # Update load balancer to point to green
        aws elbv2 modify-target-group \
          --target-group-arn $GREEN_TARGET_GROUP_ARN
    
    - name: Cleanup blue environment
      run: |
        aws ecs delete-service \
          --cluster dreamops-cluster \
          --service dreamops-backend-blue
```

## Environment Management

### Required Secrets

Add these secrets to your GitHub repository:

#### AWS Secrets
- `AWS_ACCESS_KEY_ID` - AWS access key for deployment
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `ECR_REGISTRY` - ECR registry URL
- `S3_BUCKET` - S3 bucket for frontend deployment
- `CLOUDFRONT_DISTRIBUTION_ID` - CloudFront distribution ID

#### Database Secrets
- `POSTGRES_URL_STAGING` - Staging database connection string
- `POSTGRES_URL_PROD` - Production database connection string

#### API Keys
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GITHUB_TOKEN` - GitHub API token (automatically provided)

#### Service Integrations
- `PAGERDUTY_API_KEY` - PagerDuty API key
- `AMPLIFY_APP_ID` - AWS Amplify app ID

### Environment Variables

#### Staging Environment
```bash
ENVIRONMENT=staging
DATABASE_URL=${{ secrets.POSTGRES_URL_STAGING }}
NEXT_PUBLIC_API_URL=https://api-staging.dreamops.com
K8S_ENABLED=true
LOG_LEVEL=DEBUG
```

#### Production Environment
```bash
ENVIRONMENT=production
DATABASE_URL=${{ secrets.POSTGRES_URL_PROD }}
NEXT_PUBLIC_API_URL=https://api.dreamops.com
K8S_ENABLED=true
LOG_LEVEL=INFO
```

## Monitoring and Alerting

### Deployment Monitoring

```yaml
monitor-deployment:
  runs-on: ubuntu-latest
  needs: deploy-production
  steps:
    - name: Health check
      run: |
        for i in {1..10}; do
          if curl -f https://api.dreamops.com/health; then
            echo "✅ Deployment successful"
            exit 0
          fi
          echo "⏳ Waiting for service to be ready... ($i/10)"
          sleep 30
        done
        echo "❌ Deployment failed health check"
        exit 1
    
    - name: Send deployment notification
      if: always()
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Rollback Automation

```yaml
rollback:
  runs-on: ubuntu-latest
  if: failure()
  steps:
    - name: Rollback deployment
      run: |
        # Get previous task definition
        PREVIOUS_TASK_DEF=$(aws ecs describe-services \
          --cluster dreamops-cluster \
          --services dreamops-backend \
          --query 'services[0].deployments[1].taskDefinition' \
          --output text)
        
        # Rollback to previous version
        aws ecs update-service \
          --cluster dreamops-cluster \
          --service dreamops-backend \
          --task-definition $PREVIOUS_TASK_DEF
```

## Quality Gates

### Code Quality Checks

```yaml
quality-gate:
  runs-on: ubuntu-latest
  steps:
    - name: Code coverage check
      run: |
        cd backend
        uv run pytest --cov=src --cov-report=xml
        
        # Fail if coverage below 80%
        COVERAGE=$(python -c "import xml.etree.ElementTree as ET; tree = ET.parse('coverage.xml'); print(tree.getroot().get('line-rate'))")
        if (( $(echo "$COVERAGE < 0.8" | bc -l) )); then
          echo "❌ Code coverage $COVERAGE is below 80%"
          exit 1
        fi
    
    - name: Complexity check
      run: |
        cd backend
        uv run radon cc src/ --min B
        uv run radon mi src/ --min B
```

### Performance Testing

```yaml
performance-test:
  runs-on: ubuntu-latest
  steps:
    - name: Load testing
      run: |
        # Install k6
        curl -O -L https://github.com/grafana/k6/releases/download/v0.45.0/k6-v0.45.0-linux-amd64.tar.gz
        tar -xzf k6-v0.45.0-linux-amd64.tar.gz
        
        # Run load test
        ./k6-v0.45.0-linux-amd64/k6 run tests/load-test.js
    
    - name: Performance regression check
      run: |
        # Check if response times increased significantly
        # Implementation depends on your metrics storage
        echo "Checking performance metrics..."
```

## Troubleshooting CI/CD

### Common Issues

#### Build Failures
1. **Dependency Issues**: Check `package-lock.json` or `uv.lock` for conflicts
2. **Environment Variables**: Verify all required secrets are set
3. **Test Failures**: Review test logs and fix failing tests
4. **Type Errors**: Run type checking locally before pushing

#### Deployment Failures
1. **AWS Credentials**: Verify AWS access keys have correct permissions
2. **Network Issues**: Check VPC and security group configurations
3. **Resource Limits**: Ensure sufficient ECS capacity and limits
4. **Health Checks**: Verify application health check endpoints

#### Security Scan Failures
1. **Dependency Vulnerabilities**: Update dependencies with known vulnerabilities
2. **Secret Exposure**: Remove any accidentally committed secrets
3. **Code Quality**: Fix issues identified by static analysis

### Debug Commands

```bash
# Check workflow runs
gh run list --repo your-org/oncall-agent

# View specific workflow logs
gh run view <run-id> --log

# Re-run failed jobs
gh run rerun <run-id> --failed

# Check secrets (won't show values)
gh secret list

# View deployment status
aws ecs describe-services --cluster dreamops-cluster --services dreamops-backend
```

## Best Practices

### Workflow Optimization
1. **Parallel Jobs**: Run independent jobs in parallel
2. **Caching**: Cache dependencies between runs
3. **Conditional Execution**: Skip unnecessary jobs based on changes
4. **Resource Optimization**: Use appropriate runner sizes

### Security Best Practices
1. **Least Privilege**: Grant minimal required permissions
2. **Secret Rotation**: Regularly rotate API keys and secrets
3. **Branch Protection**: Require PR reviews and status checks
4. **Dependency Scanning**: Regularly scan for vulnerabilities

### Monitoring and Observability
1. **Deployment Metrics**: Track deployment frequency and success rate
2. **Performance Monitoring**: Monitor application performance post-deployment
3. **Alert Integration**: Integrate with PagerDuty for critical failures
4. **Audit Logging**: Log all deployment activities 