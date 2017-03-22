from twisted.internet.defer import inlineCallbacks, returnValue


class GLApiCache(object):
    per_tenant_cache = {}

    @classmethod
    def add_tenant(cls, tid):
        cls.per_tenant_cache[tid] = {}

    @classmethod
    @inlineCallbacks
    def get(cls, current_tid, resource_name, language, function, *args, **kwargs):
        memory_cache_dict = cls.per_tenant_cache.get(current_tid ,{})

        if resource_name in memory_cache_dict \
                and language in memory_cache_dict[resource_name]:
            returnValue(memory_cache_dict[resource_name][language])

        value = yield function(*args, **kwargs)
        if resource_name not in memory_cache_dict:
            memory_cache_dict[resource_name] = {}
        memory_cache_dict[resource_name][language] = value
        returnValue(value)

    @classmethod
    def set(cls, current_tid, resource_name, language, value):
        memory_cache_dict = cls.per_tenant_cache.get(current_tid, {})
        if resource_name not in memory_cache_dict:
            memory_cache_dict[resource_name] = {}

        memory_cache_dict[resource_name][language] = value

    @classmethod
    def invalidate_all(cls):
        """
        Drops the cache for every tenant
        """
        cls.per_tenant_cache = {}

    @classmethod
    def invalidate(cls, current_tid, resource_name=None):
        """
        When a function is updated, all of the cached content will be dropped
        for that tenant
        """
        memory_cache_dict = cls.per_tenant_cache.get(current_tid, {})
        if resource_name is None:
            memory_cache_dict = {}
        else:
            memory_cache_dict.pop(resource_name, None)
