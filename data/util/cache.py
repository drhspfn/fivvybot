from functools import partial
from cachetools import cached, LRUCache, cachedmethod


class MyCache:
    def __init__(self):
        self.cache = LRUCache(maxsize=100)  # Используем LRU-кеш

    # Оборачиваем асинхронную функцию в декоратор cachedmethod для кеширования
    @cachedmethod(cache=partial(cached, cache=lambda self: self.cache))
    async def get_from_base_cached(self, searchID):
        return#return await get_from_base(searchID)

    # Метод для удаления значения из кеша по параметру searchID
    def delete_from_cache(self, searchID):
        del self.cache[searchID]