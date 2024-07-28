# Redis Setup Guide

   ## Ubuntu or Debian:
   ```bash
   sudo apt update
   sudo apt install redis-server
   ```

   ## macOS (using Homebrew):
   ```bash
   brew install redis
   ```

   ## Windows:
   Redis doesn't officially support Windows, but you can use the Windows Subsystem for Linux (WSL) or download the Microsoft-maintained version from https://github.com/microsoftarchive/redis/releases

   ## Using Docker:
   If you're familiar with Docker, you can run Redis in a container:
   ```bash
   docker run --name my-redis -p 6379:6379 -d redis
   ```

   ## Verify Installation:
   After installation, you can verify that Redis is running:
   ```bash
   redis-cli ping
   ```
   If Redis is running correctly, it should respond with "PONG".

   ## Start Redis (if not already running):
   On most Unix-like systems:
   ```bash
   sudo service redis-server start
   ```
   Or:
   ```bash
   redis-server
   ```

   ## Configure Redis (optional):
   The Redis configuration file is usually located at `/etc/redis/redis.conf`. You might want to review and adjust settings like:
   - `bind 127.0.0.1` (to only allow local connections)
   - `port 6379` (the default port)
   - `maxmemory 100mb` (to set a memory limit)
   - `maxmemory-policy allkeys-lru` (to evict keys when max memory is reached)

   Remember to restart Redis after changing the configuration.
   