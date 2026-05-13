from cachetools import TTLCache

# 1000 entries
# 1 hour TTL

doc_cache = TTLCache(maxsize=1000, ttl=3600)