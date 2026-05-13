# redis-client-kit

Production-ready Redis client library for Python with optional Pydantic settings, OpenTelemetry instrumentation, and Dishka dependency injection support.

## Why redis-client-kit?

- **Zero Dependencies** — Core library only depends on `redis>=7.1.0`
- **Optional Features** — Add Pydantic, OpenTelemetry, or Dishka only when you need them
- **Zero Overhead** — Plain redis-py clients when metrics aren't provided
- **Production Ready** — Battle-tested with 90%+ test coverage
- **Type Safe** — Full type hints with protocols for flexibility
- **Both Sync & Async** — Unified API for both synchronous and asynchronous code

## Features

| Feature | Status | Extra |
|---------|--------|-------|
| Async & Sync clients | ✅ Core | - |
| Redis Cluster support | ✅ Core | - |
| Connection pooling | ✅ Core | - |
| Health checks | ✅ Core | - |
| Retry logic with backoff | ✅ Core | - |
| SSL/TLS support | ✅ Core | - |
| Metrics protocol | ✅ Core | - |
| Pydantic settings | ⚙️ Optional | `[settings]` |
| Prometheus metrics | ⚙️ Optional | `[metrics]` |
| Dishka DI integration | ⚙️ Optional | `[providers]` |

## Installation

### Core only

```bash
pip install redis-client-kit
```

### With optional features

```bash
# Pydantic settings
pip install redis-client-kit[settings]

# Prometheus metrics
pip install redis-client-kit[metrics]

# Dishka dependency injection
pip install redis-client-kit[providers]

# Everything
pip install redis-client-kit[all]
```

**Requirements:** Python 3.11+

## Quick Example

```python
from redis_client_kit import create_async_redis_client
from redis_client_kit.settings import BaseRedisSettings

# Configure
settings = BaseRedisSettings(
    host="localhost",
    port=6379,
    decode_responses=True,
)

# Create client
client = create_async_redis_client(settings)

# Use it
await client.set("user:123", "John Doe")
name = await client.get("user:123")
print(name)  # "John Doe"

# Clean up
await client.aclose()
```

## Next Steps

- [Quick Start Guide](guide/quickstart/) — Get up and running in 5 minutes
- [Configuration Guide](guide/configuration/) — Learn about all configuration options
- [Advanced Usage](guide/advanced/) — Clusters, SSL, metrics, and more
- [API Reference](reference/) — Complete API documentation

## Architecture

redis-client-kit follows a layered architecture:

```
┌─────────────────────────────────────────┐
│  Optional Modules (settings, etc.)      │  [settings], [instrumentation], [providers]
├─────────────────────────────────────────┤
│  Factory Functions & Lifecycle          │  create_*, check_*, close_*
├─────────────────────────────────────────┤
│  Instrumented Clients (optional)        │  InstrumentedRedis, InstrumentedRedisCluster
├─────────────────────────────────────────┤
│  Core Protocols                         │  RedisSettingsProtocol, RedisMetricsProtocol
├─────────────────────────────────────────┤
│  redis-py (upstream)                    │  Redis, RedisCluster
└─────────────────────────────────────────┘
```

## Design Philosophy

1. **Protocols over concrete implementations** — Use `RedisSettingsProtocol` instead of forcing Pydantic
2. **Optional dependencies** — Core has zero deps beyond redis-py; extras are truly optional
3. **Zero overhead by default** — No instrumentation unless you provide metrics
4. **Production ready** — Built for real-world use with proper testing and documentation

## License

Apache 2.0 — see [LICENSE](https://github.com/bedrock-python/redis-client-kit/blob/master/LICENSE).
