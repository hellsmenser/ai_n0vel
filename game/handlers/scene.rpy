init python:
    def handle_scene(step, chars):
        renpy.scene()
        renpy.show(step.get("target"))
        return False

    register_act_handler("scene", handle_scene)
