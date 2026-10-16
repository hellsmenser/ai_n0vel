init python:
    import json

    def play_json_scene(task_id):
        path = f"scenes/scene_{task_id}.json"
        try:
            fp = renpy.loader.transfn(path)
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return
        chars = {}
        for key, name in data.get("characters", {}).items():
            chars[key] = Character(
                name,
                image=key,
                what_prefix="“",
                what_suffix="”",
                who_color="#c0c0ff"
            )

        if bg := data.get("scene"):
            renpy.scene()
            renpy.show(bg)

        handlers = get_act_handlers()

        for step in data.get("dialogue", []):
            act = step.get("type")
            handler = handlers.get(act)
            if not handler:
                continue
            should_stop = handler(step, chars)
            if should_stop:
                return

