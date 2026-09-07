# redis-client-kit for AI agents

> One page holding everything a coding assistant needs to configure and drive
> redis-client-kit correctly, plus a map of where the rest of the documentation keeps the
> details it leaves out. Give an agent this page rather than the whole site.

| | |
|---|---|
| Package | `redis-client-kit` on PyPI, import root `redis_client_kit` |
| Requires | Python 3.10+, `redis>=4.5.0,<9.0.0` (resolved at 8.1 today) |
| Install | `pip install redis-client-kit` · extras: `settings`, `metrics`, `providers`, `all` |
| Async | `redis_client_kit.aio`, re-exported from the root — returns `redis.asyncio.Redis` or `RedisCluster` |
| Sync | `redis_client_kit.sync` — same shape, different names, no `await` |
| Source | <https://github.com/bedrock-python/redis-client-kit> |

## How to read this page

Every page of this site is also served as raw Markdown at its own URL with `.md` in place
of the trailing slash — this page is `/agents.md`, the configuration guide is
`/guide/configuration.md` — so anything the map below points at can be fetched as plain
text rather than scraped out of HTML. The **Copy page** control at the top of a page does
the same thing for a human with a chat window open. The one exception is the API
reference: its Markdown is a single instruction to a docstring renderer rather than the
API, so it carries neither the control nor a `.md` twin — read it as HTML, or read the
docstrings in the source.

Top to bottom before writing code. [Rules that hold or break the code](#rules-that-hold-or-break-the-code)
is the section correctness lives in — those are the things the library will not save you
from. Every name used below is in the public API; if you need something not listed here,
fetch the page the [documentation map](#documentation-map) points at rather than guessing
a method that sounds plausible.

## Scope

**It does** build a configured `redis-py` client — single node or cluster, async or sync —
out of one settings object, wrap it in metrics when you ask for metrics, check its health,
close it without raising, and hand it to a Dishka container. The settings object can be
anything that satisfies a protocol; a Pydantic implementation with validated defaults comes
with the `settings` extra.

**It does not** wrap Redis commands. What comes back from the factory is a `redis-py`
client and everything after that call is `redis-py`'s API — there is no kit-specific `get`,
`set`, pipeline, pubsub, lock, serializer, key builder or cache. It applies no key prefix,
it does not connect for you, it runs no background task, and it retries nothing itself:
retries are `redis-py`'s `Retry`, configured from your settings.

## Mental model

Four nouns and one direction of travel.

* **Settings** — an object satisfying `RedisSettingsProtocol`: six attribute groups
  (`connection`, `cluster`, `pool`, `retry`, `ssl`, `response`) plus
  `health_check_interval`. Your own dataclass, or `BaseRedisSettings` from the `settings`
  extra.
* **The factory** — `create_async_redis_client(settings, metrics=None)` and its sync twin.
  It flattens the settings into `redis-py` keyword arguments, picks single or cluster mode
  from `settings.cluster.enabled`, and returns the client. Pass no metrics and you get a
  plain `Redis` / `RedisCluster`; pass metrics and you get `InstrumentedRedis` /
  `InstrumentedRedisCluster`, subclasses that time every `execute_command`.
* **Metrics** — anything satisfying `RedisMetricsProtocol`
  (`record_command`, `record_error`, `record_pool_stats`). `RedisMetrics` from the
  `metrics` extra is a Prometheus implementation of it.
* **Lifecycle** — `check_*_redis_health(client)` pings and returns a bool, and with
  `write_key=` writes that key as well; `close_*_redis_client(client)` closes and
  swallows. Neither raises.

Nothing here holds state of its own. The client is the state, and it is `redis-py`'s.

## Wiring

```python
from redis_client_kit import (
    check_async_redis_health,
    close_async_redis_client,
    create_async_redis_client,
)
from redis_client_kit.settings import BaseRedisSettings, RedisConnectionSettings

settings = BaseRedisSettings(
    key_prefix="myapp",                                   # required, and yours to apply
    connection=RedisConnectionSettings(host="localhost", port=6379),
)

client = create_async_redis_client(settings)              # no connection is opened here
try:
    if not await check_async_redis_health(client):
        raise RuntimeError("Redis is not answering")
    await client.set("myapp:key", "value")
finally:
    await close_async_redis_client(client)
```

The sync twin is the same text with `create_redis_client`, `check_redis_health`,
`close_redis_client` and no `await`.

Without the `settings` extra, hand the factory any object with the same attributes:

```python
from dataclasses import dataclass, field

@dataclass
class Connection:
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    client_name: str | None = None
    protocol: int = 2

    def get_password(self) -> str | None:
        return None

@dataclass
class Settings:                    # groups omitted here have defaults of their own
    connection: Connection = field(default_factory=Connection)
    ...                            # cluster, pool, retry, ssl, response
    health_check_interval: int | None = 30

client = create_async_redis_client(Settings())
```

Every attribute the protocols name has to be there: the factory reads all of them and
raises `AttributeError` on the first one missing.

## Settings

`BaseRedisSettings` (extra `settings`) is a `pydantic-settings` `BaseSettings` with
`extra="forbid"`. It is **grouped, not flat** — the six group models go in as objects, and
`key_prefix` is required.

| Field | Type | Default |
|---|---|---|
| `connection` | `RedisConnectionSettings` | all defaults |
| `cluster` | `RedisClusterSettings` | all defaults |
| `pool` | `RedisPoolSettings` | all defaults |
| `retry` | `RedisRetrySettings` | all defaults |
| `ssl` | `RedisSSLSettings` | all defaults |
| `response` | `RedisResponseSettings` | all defaults |
| `key_prefix` | `str` | **required** — never read by this library |
| `health_check_interval` | `int | None`, `ge=0` | `30` |
| `metrics_enabled` | `bool` | `False` — never read by this library |

| Group | Field | Default | Notes |
|---|---|---|---|
| `RedisConnectionSettings` | `host` | `"localhost"` | |
| | `port` | `6379` | `1 ≤ port ≤ 65535` |
| | `password` | `None` | `SecretStr`; read with `get_password()` |
| | `db` | `0` | `0 ≤ db ≤ 15`, must be `0` in cluster mode |
| | `client_name` | `None` | `CLIENT SETNAME` value |
| | `protocol` | `2` | RESP version, `2` or `3` |
| `RedisClusterSettings` | `enabled` | `False` | this alone selects cluster mode |
| | `nodes` | `None` | `["host:6379", …]`; falls back to `connection.host:port` |
| | `require_full_coverage` | `True` | |
| | `read_from_replicas` | `False` | |
| `RedisPoolSettings` | `max_connections` | `10` | `ge=1` |
| | `socket_timeout` | `5.0` | seconds |
| | `socket_connect_timeout` | `5.0` | seconds |
| | `socket_keepalive` | `True` | |
| | `socket_keepalive_options` | `None` | `dict[int, int | bytes]` |
| `RedisRetrySettings` | `enabled` | `False` | off hands `redis-py` `Retry(NoBackoff(), 0)`, not nothing — rule 5 |
| | `max_attempts` | `0` | `0` means no retry even when `enabled` |
| | `backoff_base` | `1.0` | seconds |
| | `backoff_cap` | `10.0` | seconds |
| `RedisSSLSettings` | `enabled` | `False` | |
| | `cert_reqs` | `None` | `"none"`, `"optional"`, `"required"` |
| | `ca_certs` / `certfile` / `keyfile` | `None` | paths, PEM-validated when SSL is on |
| `RedisResponseSettings` | `decode_responses` | `False` | commands return `bytes` by default |
| | `encoding` | `"utf-8"` | |

One model validator runs after construction and rejects three combinations:

1. `cluster.enabled` with neither `cluster.nodes` nor `connection.host` — `ValueError`.
2. `cluster.enabled` with `connection.db != 0` — `ValueError`.
3. `ssl.enabled` with `ssl.cert_reqs is None` — `ValueError`.

### From the environment

`BaseRedisSettings` sets no `env_prefix` and no `env_nested_delimiter`, so out of the box
the names are the bare field names and a group is one JSON document:

```bash
KEY_PREFIX=myapp
HEALTH_CHECK_INTERVAL=15
CONNECTION='{"host": "redis.internal", "port": 6380}'
```

Subclass it if you want the usual shape:

```python
from pydantic_settings import SettingsConfigDict

class Settings(BaseRedisSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_nested_delimiter="__")

# APP_KEY_PREFIX=myapp  APP_CONNECTION__HOST=redis.internal  APP_CONNECTION__PORT=6380
```

## The API

Everything in this table is importable from `redis_client_kit` itself.

| Name | Signature | Returns |
|---|---|---|
| `create_async_redis_client` | `(settings, metrics=None)` | `Redis | RedisCluster`, instrumented when `metrics` is given |
| `create_redis_client` | `(settings, metrics=None)` | the sync equivalent |
| `check_async_redis_health` | `await (client, write_key=None)` | `bool` — never raises; `write_key` adds `SET <write_key> 1 EX 60` after the ping |
| `check_redis_health` | `(client, write_key=None)` | the sync equivalent |
| `close_async_redis_client` | `await (client)` | `None` — shielded, 10 s timeout, never raises |
| `close_redis_client` | `(client)` | `None` — never raises |
| `build_base_redis_kwargs` | `(settings, asyncio=False)` | `dict[str, object]` of `redis-py` keyword arguments; `asyncio=True` for a `redis.asyncio` client |
| `build_redis_retry` | `(settings, asyncio=False)` | `redis.retry.Retry`, or `redis.asyncio.retry.Retry` with `asyncio=True` — `Retry(NoBackoff(), 0)` when retries are off |
| `parse_redis_url_node` | `(node)` | `tuple[str, int]` — `ValueError` on a node with no port |
| `AsyncRedisClient` | type alias | `redis.asyncio.Redis | redis.asyncio.cluster.RedisCluster` |
| `SyncRedisClient` | type alias | `redis.Redis | redis.cluster.RedisCluster` |
| `RedisSettingsProtocol` | protocol | what the factory reads |
| `RedisMetricsProtocol` | protocol | what instrumentation calls |
| `__version__` | `str` | |

The rest lives one import deeper.

| Module | Extra | Names |
|---|---|---|
| `redis_client_kit.aio` | — | `AsyncRedisClient`, `InstrumentedRedis`, `InstrumentedRedisCluster`, `create_async_redis_client`, `check_async_redis_health`, `close_async_redis_client` |
| `redis_client_kit.sync` | — | `SyncRedisClient`, `InstrumentedRedis`, `InstrumentedRedisCluster`, `create_redis_client`, `check_redis_health`, `close_redis_client` |
| `redis_client_kit.config` | — | `RedisSettingsProtocol` and its parts: `RedisConnectionProtocol`, `RedisClusterProtocol`, `RedisPoolProtocol`, `RedisRetryProtocol`, `RedisSSLProtocol`, `RedisResponseProtocol` |
| `redis_client_kit.protocols` | — | `RedisMetricsProtocol` |
| `redis_client_kit.utils` | — | the three exported helpers, plus `mask_redis_kwargs(kwargs)` for logging and `WRITE_PROBE_TTL_S`, the write probe's expiry in seconds |
| `redis_client_kit.settings` | `settings` | `BaseRedisSettings`, `RedisConnectionSettings`, `RedisClusterSettings`, `RedisPoolSettings`, `RedisRetrySettings`, `RedisSSLSettings`, `RedisResponseSettings` |
| `redis_client_kit.metrics` | `metrics` | `RedisMetrics`, `REDIS_COMMAND_DURATION_BUCKETS` |
| `redis_client_kit.providers` | `providers` | `AsyncRedisProvider(check_health_on_startup=True, provide_default_metrics=True)` |

Each optional module raises `ImportError` at import time when its extra is missing, naming
the extra. The root package imports none of them.

### Metrics

`RedisMetrics(prefix=None)` creates five Prometheus collectors on the default registry,
named `redis_*` or `<prefix>_redis_*`:

| Collector | Type | Labels |
|---|---|---|
| `redis_pool_size` | Gauge | — |
| `redis_pool_checked_out` | Gauge | — |
| `redis_commands_total` | Counter | `command`, `status` |
| `redis_command_duration_seconds` | Histogram | `command` |
| `redis_connection_errors_total` | Counter | `error_type` |

Buckets are `REDIS_COMMAND_DURATION_BUCKETS` — `(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05,
0.1, 0.5, 1.0, 5.0)`. They are not configurable through `RedisMetrics`; write your own
`RedisMetricsProtocol` implementation if you need different ones. `command` is the first
argument of `execute_command`, upper-cased — it is unbounded cardinality only if you send
unbounded command names.

### Dishka

```python
from dishka import Provider, Scope, make_async_container, provide

from redis_client_kit import AsyncRedisClient
from redis_client_kit.config import RedisSettingsProtocol
from redis_client_kit.metrics import RedisMetrics
from redis_client_kit.protocols import RedisMetricsProtocol
from redis_client_kit.providers import AsyncRedisProvider
from redis_client_kit.settings import BaseRedisSettings

class AppProvider(Provider):
    scope = Scope.APP

    @provide
    def settings(self) -> RedisSettingsProtocol:
        return BaseRedisSettings(key_prefix="myapp")

    @provide
    def metrics(self) -> RedisMetricsProtocol | None:      # this exact annotation
        return RedisMetrics(prefix="myapp")

container = make_async_container(AsyncRedisProvider(), AppProvider())   # this order
client = await container.get(AsyncRedisClient)
```

`AsyncRedisProvider` is `Scope.APP` and provides the client as an `AsyncIterator`, so the
container closes it on teardown. Two keyword-only constructor arguments decide what it
registers:

| Argument | Default | Effect |
|---|---|---|
| `check_health_on_startup` | `True` | pings Redis before yielding the client, and raises when it does not answer; `False` registers the factory that yields immediately |
| `provide_default_metrics` | `True` | provides `RedisMetricsProtocol | None` as `None` so a container without metrics resolves; `False` leaves that type to your own provider |

See rules 15 to 17.

## Rules that hold or break the code

1. **The factory returns a `redis-py` client, not a wrapper.** Everything after
   `create_*_redis_client` is `redis-py`: `await client.set(...)`, `client.pipeline()`,
   `client.pubsub()`. There is no kit API for commands, and no key prefixing —
   `key_prefix` is a value you carry, not behaviour you get.
2. **Creating a client opens no connection**, except for a **sync cluster** client:
   `redis.cluster.RedisCluster.__init__` discovers slots eagerly and raises
   `RedisClusterException` right there when no node answers. Async cluster and both single
   clients connect on the first command.
3. **Cluster mode is chosen by `settings.cluster.enabled`, not by the function you call.**
   With it on, `db` is never sent to the server, and `BaseRedisSettings` refuses
   `connection.db != 0` outright.
4. **Every cluster node string needs an explicit port.** `host:6379`, `[::1]:6379` and
   `redis://host:6379` parse; `redis://host` and `host` raise `ValueError`. The scheme is
   parsed and then ignored — `rediss://` does not enable TLS, `ssl.enabled` does.
5. **`retry.enabled=True` on its own retries nothing, and neither does `redis-py`.** The
   exponential `Retry` is built only when `enabled` **and** `max_attempts` are both
   truthy, and `max_attempts` defaults to `0`. Otherwise the factory hands `redis-py`
   `Retry(NoBackoff(), 0)` explicitly — never nothing, because `redis-py` given no
   `Retry` retries on its own since 6.0 (three times; ten since 8.0, with jittered
   backoff), which turns a `socket_timeout=0.5` failure into ten seconds or more. With
   retries off, the first `ConnectionError` or `TimeoutError` is the one you get. The
   flavour follows the client: the async factory hands `redis.asyncio.retry.Retry`, the
   sync factory `redis.retry.Retry`, and both helpers build the sync class unless called
   with `asyncio=True`. A sync `Retry` on a `redis.asyncio` client never retries — its
   `call_with_retry` does not await, so the failure never reaches the loop.
6. **Retries cover connection failures, not command failures.** `redis-py`'s `Retry`
   defaults to `ConnectionError`, `TimeoutError` and `socket.timeout`; a `ResponseError`
   from a bad command is raised on the first try. The delay is
   `min(backoff_cap, backoff_base * 2**failures)` with no jitter, so the first retry waits
   exactly `backoff_base`.
7. **`key_prefix` and `metrics_enabled` are declared and never read.** `key_prefix` is
   required by `BaseRedisSettings` and used by nothing in this package;
   `metrics_enabled=True` does not turn on instrumentation. Passing `metrics=` to the
   factory does, and it is the only thing that does.
8. **`BaseRedisSettings` is grouped and forbids extras.** `BaseRedisSettings(host="…")`
   raises `ValidationError: Extra inputs are not permitted`. Pass
   `connection=RedisConnectionSettings(host="…")`.
9. **`health_check_interval` is `redis-py`'s per-connection ping interval**, not the
   `check_*_redis_health` function. `0` and `None` both disable it.
10. **The health check never raises and never says "maybe", and by default it only
    pings.** It returns `False` on any error and logs it. A cluster `ping()` returns one
    entry per node, and the check is `True` only when every node answered truthily. But
    `PING` is a liveness answer, not a readiness one: a read-only replica and a server at
    `maxmemory` under `noeviction` both reply `PONG` and refuse every write. Pass
    `write_key="myapp:health"` and the check runs `SET <write_key> 1 EX 60`
    (`WRITE_PROBE_TTL_S`) after the ping, returning `False` on `ReadOnlyError`,
    `OutOfMemoryError` or anything else the write raises. The key is yours to name and
    yours to prefix — `key_prefix` is applied to nothing (rule 7) — and it is left to
    expire rather than deleted. It costs one more round trip under the same
    `socket_timeout`, and on a cluster the write reaches only the node owning that key's
    slot, so `True` there means every node answered and one of them took a write.
11. **Closing never raises either.** `close_async_redis_client` shields `aclose()` and
    gives it 10 seconds (`ACLOSE_TIMEOUT_S`); a timeout or a broken close is a warning in
    the log, not an exception. Only `CancelledError` and `KeyboardInterrupt` propagate.
12. **SSL certificate paths are read when the client is built, not when it connects.**
    With `ssl.enabled`, `build_base_redis_kwargs` opens each configured PEM file and checks
    its header, footer and base64 body: a malformed file raises `ValueError`, a missing one
    raises `FileNotFoundError`. `ssl.cert_reqs` is mandatory once SSL is on.
13. **The protocols are not `@runtime_checkable`.**
    `isinstance(settings, RedisSettingsProtocol)` raises `TypeError`. Subclass them for
    the type checker, or duck-type and let the factory's `AttributeError` find the gap.
14. **Extras are enforced at submodule import.** `import redis_client_kit` never needs
    pydantic, prometheus-client or dishka; `from redis_client_kit.settings import …`
    raises `ImportError` naming the extra when it is missing. Do not guard the root
    import.
15. **Register `AsyncRedisProvider()` before your own metrics provider, or turn its
    default off.** It provides a default `RedisMetricsProtocol | None` of `None`, and in
    Dishka the last provider to claim a type wins — put it second and your metrics are
    silently dropped, leaving an uninstrumented client.
    `AsyncRedisProvider(provide_default_metrics=False)` registers no default, so order
    stops mattering. Either way the annotation on your factory must be exactly
    `RedisMetricsProtocol | None`; `RedisMetricsProtocol` is a different key.
16. **The provider registers one client factory, chosen at construction.**
    `AsyncRedisProvider()` registers `get_redis_with_health_check()`;
    `AsyncRedisProvider(check_health_on_startup=False)` registers `get_redis()` instead.
    They provide the same type, so registering both would leave only the second — the
    constructor picks one.
17. **The provider's startup health check fails startup.** It pings up to three times
    with exponential backoff — 1 s, then 2 s — and raises `ConnectionError` when Redis
    never answers, closing the client it built. Resolving `AsyncRedisClient` is what
    triggers it, so that is where the error surfaces. Use
    `AsyncRedisProvider(check_health_on_startup=False)` when a missing Redis must not
    block startup.
18. **A `RedisMetrics` instance owns global Prometheus names.** Building a second one with
    the same prefix raises a duplicate-timeseries `ValueError` from the default registry.
    Build one per process and inject it.
19. **Cluster clients record no pool statistics.** Single-node clients, async and sync,
    report `redis_pool_size` and `redis_pool_checked_out` from the pool's own containers
    before every command; `InstrumentedRedisCluster` reports neither. Command counts,
    durations and error counts are recorded everywhere.
20. **A uvloop closed-transport `RuntimeError` reaches you as `redis-py`'s
    `ConnectionError`.** `execute_command` translates it so `redis-py` can retry or
    reconnect, and records it under the type you catch:
    `redis_commands_total{status="error"}` and
    `redis_connection_errors_total{error_type="ConnectionError"}`. Catch
    `redis.exceptions.ConnectionError`, not `RuntimeError`. Any other `RuntimeError` is
    re-raised unchanged and counted under `RuntimeError`.

## Common mistakes

```python
# WRONG — the flat constructor from an older version of this library
settings = BaseRedisSettings(host="localhost", port=6379, decode_responses=True)

# RIGHT — grouped, and key_prefix is required
settings = BaseRedisSettings(
    key_prefix="myapp",
    connection=RedisConnectionSettings(host="localhost", port=6379),
    response=RedisResponseSettings(decode_responses=True),
)
```

```python
# WRONG — retry that never retries, and a cluster node with no port
BaseRedisSettings(
    key_prefix="myapp",
    retry=RedisRetrySettings(enabled=True),                 # max_attempts is still 0
    cluster=RedisClusterSettings(enabled=True, nodes=["redis://node1"]),
)                       # accepted here, ValueError when the factory parses the node

# RIGHT
BaseRedisSettings(
    key_prefix="myapp",
    retry=RedisRetrySettings(enabled=True, max_attempts=3, backoff_base=0.5, backoff_cap=5.0),
    cluster=RedisClusterSettings(enabled=True, nodes=["node1:6379", "node2:6379"]),
)
```

```python
# WRONG — a sync Retry on an async client never retries: its call_with_retry does not await
client = redis.asyncio.Redis(**build_base_redis_kwargs(settings), host="localhost", port=6379)

# RIGHT — asyncio=True builds redis.asyncio.retry.Retry, which is what the async factory does
client = redis.asyncio.Redis(**build_base_redis_kwargs(settings, asyncio=True), host="localhost", port=6379)
```

```python
# WRONG — metrics_enabled does nothing, and the client is never instrumented
settings = BaseRedisSettings(key_prefix="myapp", metrics_enabled=True)
client = create_async_redis_client(settings)

# RIGHT
client = create_async_redis_client(settings, metrics=RedisMetrics(prefix="myapp"))
```

```python
# WRONG — creating a client is not connecting to one
client = create_async_redis_client(settings)
log.info("Redis is up")

# RIGHT
client = create_async_redis_client(settings)
if not await check_async_redis_health(client):
    raise RuntimeError("Redis is not answering")
```

```python
# WRONG — readiness for a service that writes, from a check a read-only replica passes
if not await check_async_redis_health(client):
    return Response("unready", status_code=503)

# RIGHT — ask for the write you are going to need
if not await check_async_redis_health(client, write_key="myapp:health"):
    return Response("unready", status_code=503)
```

```python
# WRONG — a per-request client, and a close that can take the request down with it
async def handler(settings):
    client = create_async_redis_client(settings)
    try:
        return await client.get("key")
    finally:
        await client.aclose()

# RIGHT — one client per process, closed once, with the shielded helper
client = create_async_redis_client(settings)      # at startup
...
await close_async_redis_client(client)            # at shutdown
```

## Errors

This library defines no exception classes of its own. Everything you catch is raised by
Python, by Pydantic or by `redis-py`.

| Raised by | What it is |
|---|---|
| `ValueError` from `parse_redis_url_node` | an empty node, a node with no port, or a port outside 1-65535 |
| `ValueError` / `FileNotFoundError` from `build_base_redis_kwargs` | a malformed or missing PEM file while `ssl.enabled` |
| `pydantic.ValidationError` from `BaseRedisSettings` | a field out of range, an unknown keyword, a missing `key_prefix`, or one of the validator's three checks |
| `AttributeError` from the factory | a settings object missing an attribute the protocols name |
| `redis.exceptions.*` from the client | everything at run time: `ConnectionError`, `TimeoutError`, `ResponseError`, `RedisClusterException`, `ClusterDownError` and the rest of `redis-py`'s tree, all under `RedisError` |
| builtin `ConnectionError` from `AsyncRedisProvider` | Redis did not answer within the startup health check's three attempts — Python's `ConnectionError`, not `redis.exceptions.ConnectionError`, so it is not caught by `except RedisError` |
| `ImportError` from an optional submodule | the extra is not installed; the message names it |

`check_*_redis_health` and `close_*_redis_client` convert `redis-py`'s errors into a
`False` and a log line respectively — they are the two places that swallow. A refused
write probe goes the same way: `ReadOnlyError` and `OutOfMemoryError` come back as `False`
with a warning in the log, not as an exception.

## Documentation map

Fetch a page when the task is the one named beside it.

| Page | Read it when |
|---|---|
| [Home](index.md) | the shape of the library and what each extra adds |
| [Quick start](guide/quickstart.md) | the lifecycle helpers, the context-manager pattern, `redis-py` command examples |
| [Configuration](guide/configuration.md) | implementing `RedisSettingsProtocol` without Pydantic |
| [Advanced](guide/advanced.md) | writing a `RedisMetricsProtocol`, Dishka wiring, cluster and TLS deployment notes |
| [API reference](reference/index.md) | an exact signature or docstring — HTML only, see above |
| [Changelog](changelog.md) | what changed between versions |
