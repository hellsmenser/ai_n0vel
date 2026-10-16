init -10 python:
    ACT_HANDLERS_REGISTRY = {}

    def register_act_handler(name, func):
        ACT_HANDLERS_REGISTRY[name] = func

    def act_handler(name):
        def deco(fn):
            register_act_handler(name, fn)
            return fn
        return deco

    def get_act_handlers():
        return ACT_HANDLERS_REGISTRY.copy()

    def clear_act_handlers():
        ACT_HANDLERS_REGISTRY.clear()
