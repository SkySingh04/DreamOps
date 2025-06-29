# Grafana Integration Test Suite

This directory contains comprehensive tests for the Grafana MCP integration in the OnCall Agent.

## Test Structure

```
tests/integrations/grafana/
├── conftest.py                 # Pytest configuration and fixtures
├── test_grafana_integration.py # Comprehensive test suite
├── docker-compose.yml          # Test environment setup
├── grafana-provisioning/       # Grafana configuration
├── prometheus-config/          # Prometheus configuration
├── sample-app-config/          # Sample app for metrics
└── README.md                   # This file
```

## Quick Start

### 1. Using Docker (Recommended)

Start the test environment:
```bash
cd tests/integrations/grafana/
docker-compose up -d
```

Wait for services to be ready (check with `docker-compose ps`), then create an API key:
1. Open http://localhost:3000 (admin/admin123)
2. Go to Configuration → API Keys
3. Create new key with Admin role
4. Copy the generated key

Run tests:
```bash
export GRAFANA_MCP_URL=http://localhost:3000
export GRAFANA_MCP_API_KEY=your-generated-api-key
pytest test_grafana_integration.py -v
```

Stop the environment:
```bash
docker-compose down -v
```

### 2. Using External Grafana

Set environment variables:
```bash
export GRAFANA_MCP_URL=https://your-grafana-instance.com
export GRAFANA_MCP_API_KEY=your-api-key
```

Run tests:
```bash
pytest test_grafana_integration.py -v
```

## Test Categories

### Connection Tests (`TestGrafanaConnection`)
- Basic connection and health checks
- Capability verification
- Connection retry mechanism
- Authentication validation

### Dashboard Operations (`TestDashboardOperations`)
- List dashboards with performance benchmarks
- Search functionality
- Dashboard creation (requires permissions)
- Complete CRUD workflow testing

### Metrics Operations (`TestMetricsOperations`)
- Simple and complex metric queries
- Various time range testing
- Incident-specific metrics collection
- Performance benchmarks for queries

### Alert Operations (`TestAlertOperations`)
- List current alerts
- Alert rule creation (requires permissions)
- Alert silencing functionality

### Data Source Operations (`TestDataSourceOperations`)
- List available data sources
- Validate data source structure

### Error Scenarios (`TestErrorScenarios`)
- Invalid context types and actions
- Malformed queries
- Connection state validation
- Graceful error handling

### Performance Benchmarks (`TestPerformanceBenchmarks`)
- Concurrent query execution
- Pagination performance
- Response time validation

### Agent Integration (`TestIntegrationWithAgent`)
- Context gathering simulation
- Service-specific metrics collection
- End-to-end workflow testing

## Test Configuration

### Environment Variables

Required:
- `GRAFANA_MCP_URL` or `GRAFANA_URL` - Grafana instance URL
- `GRAFANA_MCP_API_KEY` or `GRAFANA_API_KEY` - Grafana API key

Optional:
- `GRAFANA_USERNAME` - Alternative to API key
- `GRAFANA_PASSWORD` - Alternative to API key

### Pytest Markers

- `@pytest.mark.grafana` - Requires Grafana connection
- `@pytest.mark.slow` - Longer running tests
- `@pytest.mark.requires_permissions` - Needs specific Grafana permissions

### Fixtures

- `grafana_config` - Configuration dictionary
- `grafana_integration` - Connected integration instance
- `grafana_client` - Direct HTTP client for setup/teardown
- `test_dashboard_data` - Sample dashboard data
- `test_alert_rule_data` - Sample alert rule data
- `performance_threshold` - Performance benchmarks
- `cleanup_test_dashboards` - Automatic cleanup after tests

## Docker Test Environment

The included `docker-compose.yml` provides:

### Services
- **Grafana** (port 3000) - Main testing target
- **Prometheus** (port 9090) - Metrics data source
- **Node Exporter** (port 9100) - System metrics
- **Sample App** (port 8080) - Custom metrics endpoint

### Pre-configured
- Default admin credentials: admin/admin123
- Prometheus data source configured
- Test dashboard with sample panels
- Sample metrics for testing queries

### Health Checks
All services include health checks to ensure they're ready for testing.

## Running Specific Tests

### All Grafana tests:
```bash
pytest -m grafana -v
```

### Only fast tests:
```bash
pytest -m "grafana and not slow" -v
```

### Performance benchmarks:
```bash
pytest -m "grafana and slow" -v
```

### Connection tests only:
```bash
pytest -k "TestGrafanaConnection" -v
```

### With detailed output:
```bash
pytest test_grafana_integration.py::TestDashboardOperations::test_list_dashboards -v -s
```

## Expected Test Behavior

### With Full Permissions (Admin API Key)
- All tests should pass
- Dashboard creation/modification works
- Alert rule operations succeed
- Full CRUD operations available

### With Limited Permissions (Viewer API Key)
- Connection and read operations succeed
- Write operations fail gracefully with 403 errors
- Tests validate proper error handling
- No false failures due to permission restrictions

### With Grafana Cloud
- Some operations may not be available (404 errors)
- Tests handle cloud-specific limitations
- Fallback mechanisms are tested
- Compatibility is verified

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure Grafana is running and accessible
   - Check URL and port configuration
   - Verify network connectivity

2. **Authentication Errors**
   - Verify API key is valid and not expired
   - Check API key permissions
   - Ensure Bearer token format is correct

3. **Permission Errors (403)**
   - Expected with viewer-level API keys
   - Tests should handle gracefully
   - Create admin API key for full testing

4. **Docker Issues**
   - Check if ports are already in use
   - Ensure Docker daemon is running
   - Try `docker-compose down -v` and restart

5. **Test Skips**
   - Set required environment variables
   - Check Grafana connectivity
   - Verify pytest markers

### Debug Mode

Run with verbose output and no capture:
```bash
pytest test_grafana_integration.py -v -s --tb=short
```

Show all test discovery:
```bash
pytest --collect-only -q
```

## Integration with CI/CD

### GitHub Actions Example
```yaml
- name: Start Grafana Test Environment
  run: |
    cd tests/integrations/grafana/
    docker-compose up -d
    sleep 30  # Wait for services to start

- name: Run Grafana Tests
  env:
    GRAFANA_MCP_URL: http://localhost:3000
    GRAFANA_MCP_API_KEY: ${{ secrets.GRAFANA_TEST_API_KEY }}
  run: |
    pytest tests/integrations/grafana/ -v --tb=short

- name: Cleanup Test Environment
  run: |
    cd tests/integrations/grafana/
    docker-compose down -v
```

## Performance Expectations

### Response Time Thresholds
- Dashboard list: < 2 seconds
- Dashboard get: < 1 second
- Simple query: < 3 seconds
- Complex query: < 5 seconds
- Alert list: < 2 seconds
- Annotation query: < 2 seconds

### Concurrent Operations
- 3 simultaneous queries should complete within 10 seconds
- No degradation with pagination
- Proper connection pooling

## Security Considerations

### Test Data
- All test dashboards use `test_oncall_` prefix
- Automatic cleanup after tests
- No production data modification

### Credentials
- Test API keys should have minimal required permissions
- Use separate test instance when possible
- Never commit credentials to repository

### Network
- Docker network isolation
- No external network access required for container tests
- Localhost binding for security

## Related Files

- `../../test_grafana_mcp.py` - Quick standalone test
- `../../test_grafana_setup.py` - Setup verification
- `../../test_grafana_e2e.py` - End-to-end with agent
- `../../../src/oncall_agent/mcp_integrations/grafana_mcp.py` - Implementation