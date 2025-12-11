# XSP-Lib Configuration Examples

This directory contains example TOML configuration files for Phase 4 production features.

## Configuration Files

### `config_production.toml`
Production-ready configuration with:
- **Dialer Settings**: Connection pooling optimized for high-traffic scenarios
  - 200 max connections with 60 keepalive connections
  - 10-second timeout for VAST requests
  - 30-second cleanup interval
  
- **Session Management**: Production-scale session tracking
  - 100,000 max concurrent sessions
  - 24-hour session timeout
  - 1-hour cleanup interval

- **Frequency Capping** (IAB QAG Compliant):
  - Global: 5 impressions per 24 hours
  - Per-campaign overrides available
  - Redis backend for distributed deployments
  - Supports both global and per-campaign caps

- **Budget Tracking**:
  - Decimal precision for financial accuracy
  - Per-campaign budgets with pacing
  - Redis backend with atomic updates
  - Example campaigns: $50k, $100k, $75k budgets

- **Production Features**:
  - TLS/SSL verification enabled
  - Retry with exponential backoff
  - Circuit breaker for fault tolerance
  - JSON logging for aggregation
  - Prometheus metrics

### `config_development.toml`
Development-friendly configuration with:
- **Smaller Resource Limits**: 20 connections (vs 200 in production)
- **Faster Timeouts**: 3-5 seconds for quicker feedback
- **Debug Logging**: Enabled with text format for readability
- **In-Memory Storage**: No Redis/database required
- **Looser Frequency Caps**: 20 impressions per hour for easier testing
- **Small Test Budgets**: $10, $50, $200 for quick testing
- **Relaxed Security**: SSL verification disabled for self-signed certs
- **Mock Mode Support**: Test without external dependencies

## Usage

### Python Application

Load configuration using Python's `tomli` (built-in on Python 3.11+) or `toml`:

```python
import tomllib  # Python 3.11+
# Or: import tomli as tomllib  # Python 3.10 and earlier

from decimal import Decimal
from xsp.core.dialer import HttpDialer
from xsp.middleware.frequency import FrequencyCap, FrequencyCappingMiddleware, InMemoryFrequencyStore
from xsp.middleware.budget import Budget, BudgetTrackingMiddleware, InMemoryBudgetStore

# Load configuration
with open("config_production.toml", "rb") as f:
    config = tomllib.load(f)

# Create dialer with configured pool settings
dialer = HttpDialer(
    pool_limits={
        "max_connections": config["dialer"]["max_connections"],
        "max_keepalive_connections": config["dialer"]["max_keepalive_connections"]
    },
    timeout=config["dialer"]["timeout"]
)

# Setup frequency capping from config
freq_config = config["frequency_capping"]["global"]
frequency_cap = FrequencyCap(
    max_impressions=freq_config["max_impressions"],
    time_window_seconds=freq_config["time_window_seconds"],
    per_campaign=freq_config["per_campaign"]
)

# Setup budget tracking from config
budget_config = config["budget_tracking"]
budgets = {}
for campaign in budget_config["campaigns"]:
    budget = Budget(
        total_budget=Decimal(campaign["total_budget"]),
        spent=Decimal(campaign["spent"]),
        currency=budget_config["currency"],
        campaign_id=campaign["campaign_id"]
    )
    budgets[campaign["campaign_id"]] = budget
```

### Environment-Specific Configuration

Choose configuration based on environment:

```python
import os
import tomllib

env = os.getenv("ENV", "development")
config_file = f"config_{env}.toml"

with open(config_file, "rb") as f:
    config = tomllib.load(f)
```

### Validation

Validate configuration before application startup:

```python
def validate_config(config: dict) -> None:
    """Validate configuration structure and values."""
    
    # Validate dialer settings
    assert config["dialer"]["max_connections"] > 0, "max_connections must be positive"
    assert config["dialer"]["max_keepalive_connections"] <= config["dialer"]["max_connections"]
    
    # Validate frequency capping
    if config["frequency_capping"]["enabled"]:
        assert config["frequency_capping"]["global"]["max_impressions"] > 0
        assert config["frequency_capping"]["global"]["time_window_seconds"] > 0
    
    # Validate budget tracking
    if config["budget_tracking"]["enabled"]:
        assert len(config["budget_tracking"]["currency"]) == 3, "Currency must be ISO 4217 code"
        for campaign in config["budget_tracking"]["campaigns"]:
            total = Decimal(campaign["total_budget"])
            spent = Decimal(campaign["spent"])
            assert total >= spent, f"Campaign {campaign['campaign_id']}: spent exceeds total"
    
    print("✓ Configuration valid")

# Validate before using
validate_config(config)
```

## Configuration Sections

### Dialer (Connection Pooling)

Controls HTTP connection pool behavior:

| Setting | Production | Development | Description |
|---------|-----------|-------------|-------------|
| `max_connections` | 200 | 20 | Total connection pool size |
| `max_keepalive_connections` | 60 | 5 | Idle connections to keep alive |
| `timeout` | 10.0 | 5.0 | Request timeout (seconds) |
| `cleanup_interval` | 30.0 | 10.0 | Pool cleanup frequency (seconds) |

### Session Management

Manages request context and user state:

| Setting | Production | Development | Description |
|---------|-----------|-------------|-------------|
| `enabled` | true | true | Enable session tracking |
| `session_timeout` | 86400 | 3600 | Session expiry (seconds) |
| `max_concurrent_sessions` | 100000 | 1000 | Maximum active sessions |
| `cleanup_interval` | 3600 | 300 | Cleanup frequency (seconds) |

### Frequency Capping

IAB QAG-compliant ad frequency control:

| Setting | Production | Development | Description |
|---------|-----------|-------------|-------------|
| `enabled` | true | true | Enable frequency capping |
| `max_impressions` | 5 | 20 | Max impressions per window |
| `time_window_seconds` | 86400 | 3600 | Cap time window (24h vs 1h) |
| `per_campaign` | false | false | Per-campaign vs global |
| `storage.backend` | redis | memory | Storage backend |

**IAB QAG Recommendations:**
- Video ads: 3-10 impressions per 24 hours
- Interstitials: 2-3 impressions per 12-24 hours
- Standard display: 10-20 impressions per 24 hours

### Budget Tracking

Real-time campaign budget monitoring:

| Setting | Production | Development | Description |
|---------|-----------|-------------|-------------|
| `enabled` | true | true | Enable budget tracking |
| `default_cost` | "0.005" | "0.10" | Default CPM/1000 |
| `currency` | "USD" | "USD" | ISO 4217 currency code |
| `per_campaign` | true | true | Per-campaign budgets |
| `storage.backend` | redis | memory | Storage backend |
| `updates.atomic_updates` | true | true | Prevent race conditions |

**Example Campaign Budgets:**

Production:
- Premium Brand: $50,000 over 30 days with pacing
- Performance: $100,000 over 60 days with pacing
- Retargeting: $75,000 over 45 days with pacing

Development:
- Small Test: $10 (no pacing)
- Medium Test: $50 (7 days pacing)
- Large Test: $200 (30 days pacing)

## Storage Backends

### In-Memory (Development Only)

```toml
[frequency_capping.storage]
backend = "memory"
```

**Pros:**
- No external dependencies
- Fast and simple
- Good for testing

**Cons:**
- Data lost on restart
- Not suitable for distributed deployments
- Single instance only

### Redis (Production Recommended)

```toml
[frequency_capping.storage]
backend = "redis"

[frequency_capping.storage.redis]
host = "localhost"
port = 6379
db = 0
password = ""
max_connections = 50
key_prefix = "freq:"
ssl = false
```

**Pros:**
- Persistent storage
- Distributed deployment support
- Atomic operations
- High performance

**Cons:**
- Requires Redis server
- Additional infrastructure

## Per-Campaign Overrides

Both production and development configs support per-campaign settings:

```toml
# Global default
[frequency_capping.global]
max_impressions = 5
time_window_seconds = 86400

# Campaign-specific override
[[frequency_capping.campaigns]]
campaign_id = "premium-brand-campaign"
max_impressions = 3  # Stricter than global
time_window_seconds = 86400
```

Campaigns without overrides use global settings.

## Migration from In-Memory to Redis

When moving from development to production:

1. **Install Redis:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS
   brew install redis
   
   # Or use Docker
   docker run -d -p 6379:6379 redis:7-alpine
   ```

2. **Update Configuration:**
   ```toml
   [frequency_capping.storage]
   backend = "redis"  # Change from "memory"
   
   [frequency_capping.storage.redis]
   host = "your-redis-host"
   port = 6379
   ```

3. **Test Connection:**
   ```python
   import redis
   
   r = redis.Redis(host='localhost', port=6379, db=0)
   r.ping()  # Should return True
   ```

4. **Update Application Code:**
   ```python
   from xsp.middleware.frequency import RedisFrequencyStore
   
   # Replace InMemoryFrequencyStore with RedisFrequencyStore
   frequency_store = RedisFrequencyStore(
       host=config["frequency_capping"]["storage"]["redis"]["host"],
       port=config["frequency_capping"]["storage"]["redis"]["port"],
       db=config["frequency_capping"]["storage"]["redis"]["db"],
   )
   ```

## Best Practices

### Production Checklist

- [ ] Use `config_production.toml` as template
- [ ] Enable Redis for frequency capping and budget tracking
- [ ] Set appropriate connection pool sizes based on traffic
- [ ] Enable TLS/SSL verification (`verify_ssl = true`)
- [ ] Configure proper timeouts (VAST: 8-10s, OpenRTB: 150ms)
- [ ] Enable JSON logging for log aggregation
- [ ] Configure Prometheus metrics
- [ ] Test frequency cap behavior with real traffic patterns
- [ ] Validate budget tracking accuracy with Decimal precision
- [ ] Set up monitoring alerts for budget exhaustion
- [ ] Configure circuit breakers for upstream failures

### Development Checklist

- [ ] Use `config_development.toml` as template
- [ ] In-memory storage is sufficient for local testing
- [ ] Enable DEBUG logging for troubleshooting
- [ ] Disable SSL verification for self-signed certs
- [ ] Use small budgets ($10-$200) for quick testing
- [ ] Set short frequency cap windows (5-30 minutes)
- [ ] Test budget exhaustion scenarios
- [ ] Test frequency cap exceeded errors
- [ ] Verify configuration validation logic

### Security Considerations

1. **Never commit secrets to version control:**
   ```toml
   # BAD - in config file
   password = "super-secret-password"
   
   # GOOD - use environment variables
   password = "${REDIS_PASSWORD}"
   ```

2. **Use environment-specific configs:**
   - Keep production credentials separate
   - Use different Redis databases per environment
   - Different key prefixes to avoid collisions

3. **Enable SSL/TLS in production:**
   ```toml
   [security]
   verify_ssl = true  # Always in production
   
   [frequency_capping.storage.redis]
   ssl = true  # Enable for production Redis
   ```

## Troubleshooting

### Connection Pool Exhausted

**Symptom:** Errors about no available connections

**Solution:** Increase `max_connections`:
```toml
[dialer]
max_connections = 300  # Increase from 200
```

### Frequency Cap Not Working

**Symptom:** Users see more ads than configured

**Checks:**
1. Verify middleware is enabled
2. Check user_id is being passed correctly
3. Verify storage backend is working
4. Check time_window_seconds calculation

### Budget Tracking Inaccurate

**Symptom:** Budget spent doesn't match actual impressions

**Checks:**
1. Ensure using Decimal, not float
2. Verify atomic_updates is enabled
3. Check Redis connection
4. Validate cost calculation logic

### Redis Connection Failed

**Symptom:** Cannot connect to Redis

**Solutions:**
1. Verify Redis is running: `redis-cli ping`
2. Check host/port settings in config
3. Verify firewall allows connections
4. Check Redis authentication

## Examples

See the example Python scripts in this directory:
- `budget_tracking.py` - Budget tracking demonstrations
- `frequency_capping.py` - Frequency capping demonstrations
- `vast_example.py` - VAST protocol usage
- `basic_http.py` - HTTP transport usage

## References

- **IAB VAST 4.2**: https://iabtechlab.com/vast/
- **IAB OpenRTB 2.6**: https://iabtechlab.com/openrtb/
- **IAB QAG**: Quality Assurance Guidelines
- **HTTPX Documentation**: https://www.python-httpx.org/
- **Redis Documentation**: https://redis.io/documentation

## Support

For questions or issues:
1. Check example scripts in this directory
2. Review inline comments in config files
3. See main documentation at `/docs`
4. Open an issue on GitHub
