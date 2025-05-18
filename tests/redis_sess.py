import redis

redis_sesss = redis.from_url("redis://localhost:6379")

redis_sesss.setex('key1', 1000, 'value100')