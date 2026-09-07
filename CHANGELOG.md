# Changelog

## [0.2.0](https://github.com/bedrock-python/redis-client-kit/compare/redis-client-kit-v0.1.5...redis-client-kit-v0.2.0) (2026-09-07)


### Features

* add an opt-in write probe to the health checks ([#32](https://github.com/bedrock-python/redis-client-kit/issues/32)) ([aabafd1](https://github.com/bedrock-python/redis-client-kit/commit/aabafd1922e3e0cf1b525570f98cdf0f71a2856e))

## [0.1.5](https://github.com/bedrock-python/redis-client-kit/compare/redis-client-kit-v0.1.4...redis-client-kit-v0.1.5) (2026-09-07)


### Bug Fixes

* hand redis.asyncio.Redis the async Retry, not the sync one ([#29](https://github.com/bedrock-python/redis-client-kit/issues/29)) ([e8ee302](https://github.com/bedrock-python/redis-client-kit/commit/e8ee3024b8e402cdb80c531b9284d513111116ea))

## [0.1.4](https://github.com/bedrock-python/redis-client-kit/compare/redis-client-kit-v0.1.3...redis-client-kit-v0.1.4) (2026-09-07)


### Bug Fixes

* hand redis-py a zero-retry Retry when retries are disabled ([#27](https://github.com/bedrock-python/redis-client-kit/issues/27)) ([02d4f55](https://github.com/bedrock-python/redis-client-kit/commit/02d4f5590b6bcdc26d8d13c81cfc80bfd3551f1a))

## [0.1.3](https://github.com/bedrock-python/redis-client-kit/compare/redis-client-kit-v0.1.2...redis-client-kit-v0.1.3) (2026-09-06)


### Bug Fixes

* fail startup on an unreachable Redis, and count translated errors as errors ([#23](https://github.com/bedrock-python/redis-client-kit/issues/23)) ([38187bb](https://github.com/bedrock-python/redis-client-kit/commit/38187bb202f14e8f893e7597926f0cb3cb750b80))

## [0.1.2](https://github.com/bedrock-python/redis-client-kit/compare/redis-client-kit-v0.1.1...redis-client-kit-v0.1.2) (2026-09-05)


### Bug Fixes

* update publish workflow, release-please version search, gitignore ([#5](https://github.com/bedrock-python/redis-client-kit/issues/5)) ([9f82f2b](https://github.com/bedrock-python/redis-client-kit/commit/9f82f2b8cec5d6f32a9184337ddfc3ef3b68b7d3))

## 0.1.1 (2026-05-13)


### Bug Fixes

* correct Python version requirement to 3.10+ ([2764531](https://github.com/bedrock-python/redis-client-kit/commit/2764531eea98083dcd194a3721dbca524a5f926a))

## 0.1.0 (2026-05-13)


### Features

* initial redis-client-kit library ([7f2eda5](https://github.com/bedrock-python/redis-client-kit/commit/7f2eda5350c3bb5ae460f2312508daf216c49adf))

## Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
