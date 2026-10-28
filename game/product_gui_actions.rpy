init -60 python:
    def product_gui_update(callback, *args):
        """Runs a model mutation without returning a value to screen actions.

        Ren'Py treats any non-None Function result as the result of the current
        interaction. The model functions intentionally return values for tests
        and other callers, so GUI bindings go through this adapter instead.
        """
        callback(*args)
        return None

    def product_gui_select_asset(asset_id):
        """Selects a library card without relying on a transient screen context."""
        item = asset_catalog_get(asset_id)
        screen = renpy.get_screen("asset_library")
        if item is None or screen is None:
            return None
        screen.scope["asset_category"] = item["category"]
        screen.scope["selected_asset_id"] = item["id"]
        screen.scope["description_buffer"] = asset_catalog_description(item["id"])
        renpy.restart_interaction()
        return None

    def product_gui_select_asset_category(category_id):
        entries = asset_catalog_entries(category_id, include_hidden=False)
        if entries:
            return product_gui_select_asset(entries[0]["id"])
        return None

    class ProductGuiStartStory(Action):
        """Commits a valid draft before leaving the product shell."""

        def __call__(self):
            if not story_builder_commit():
                renpy.restart_interaction()
                return None
            return renpy.run(Start())

        def get_sensitive(self):
            return not story_draft_validate()
