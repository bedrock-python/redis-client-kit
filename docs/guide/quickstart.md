# Quick Start

Get up and running with redis-client-kit in minutes.

## Installation

```bash
pip install redis-client-kit
```

For Pydantic settings support:

```bash
pip install redis-client-kit[settings]
```

## Basic Usage

### Async Client

```python
from redis_client_kit import create_async_redis_client
from redis_client_kit.settings import BaseRedisSettings

# Configure
settings = BaseRedisSettings(
    host="localhost",
    port=6379,
)

# Create client
client = create_async_redis_client(settings)

# Use it
await client.set("key", "value")
value = await client.get("key")
print(value)  # b"value"

# Clean up
await client.aclose()
```

### Sync Client

```python
from redis_client_kit.sync import create_redis_client
from redis_client_kit.settings import BaseRedisSettings

settings = BaseRedisSettings(host="localhost", port=6379)
client = create_redis_client(settings)

client.set("key", "value")
value = client.get("key")
print(value)  # b"value"

client.close()
```

## Decode Responses

By default, Redis returns bytes. Enable `decode_responses` to get strings:

```python
settings = BaseRedisSettings(
    host="localhost",
    port=6379,
    decode_responses=True,  # Return strings instead of bytes
)

client = create_async_redis_client(settings)
await client.set("key", "value")
value = await client.get("key")
print(value)  # "value" (string, not bytes)
```

## Health Checks

Check if Redis is healthy and ready:

```python
from redis_client_kit import check_async_redis_health

is_healthy = await check_async_redis_health(client)
if is_healthy:
    print("Redis is ready!")
else:
    print("Redis is not available")
```

## Graceful Shutdown

Always close the client properly:

```python
from redis_client_kit import close_async_redis_client

# Safe cleanup with timeout protection
await close_async_redis_client(client)
```

## Context Manager Pattern

Use async context managers for automatic cleanup:

```python
from contextlib import asynccontextmanager
from redis_client_kit import create_async_redis_client, close_async_redis_client

@asynccontextmanager
async def redis_client(settings):
    client = create_async_redis_client(settings)
    try:
        yield client
    finally:
        await close_async_redis_client(client)

# Usage
async with redis_client(settings) as client:
    await client.set("key", "value")
    # Automatic cleanup on exit
```

## Connection Pooling

Connection pooling is enabled by default:

```python
settings = BaseRedisSettings(
    host="localhost",
    port=6379,
    max_connections=20,  # Pool size
    socket_timeout=5.0,   # Socket timeout in seconds
)

client = create_async_redis_client(settings)
```

## Error Handling

Handle Redis errors gracefully:

```python
from redis.exceptions import RedisError, ConnectionError, TimeoutError

try:
    await client.set("key", "value")
except ConnectionError:
    print("Cannot connect to Redis")
except TimeoutError:
    print("Redis operation timed out")
except RedisError as e:
    print(f"Redis error: {e}")
```

## Basic Operations

```python
# Strings
await client.set("name", "Alice")
name = await client.get("name")

# Expiration
await client.setex("session", 3600, "token123")  # Expires in 1 hour
await client.expire("name", 60)  # Set TTL to 60 seconds
ttl = await client.ttl("name")

# Delete
await client.delete("name")

# Check existence
exists = await client.exists("name")

# Increment/Decrement
await client.set("counter", 0)
await client.incr("counter")  # 1
await client.incrby("counter", 5)  # 6
await client.decr("counter")  # 5

# Hashes
await client.hset("user:123", "name", "Alice")
await client.hset("user:123", "age", 30)
name = await client.hget("user:123", "name")
user_data = await client.hgetall("user:123")

# Lists
await client.lpush("queue", "item1", "item2")
item = await client.rpop("queue")

# Sets
await client.sadd("tags", "python", "redis", "async")
members = await client.smembers("tags")
is_member = await client.sismember("tags", "python")

# Sorted Sets
await client.zadd("scores", {"Alice": 100, "Bob": 85})
top = await client.zrange("scores", 0, -1, withscores=True)
```

## Next Steps

- [Configuration Guide](configuration.md) — Learn about all settings
- [Advanced Usage](advanced.md) — Clusters, SSL, metrics
- [API Reference](../reference/) — Complete API documentation
