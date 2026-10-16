init python:
    def handle_jump(step, chars):
        renpy.jump(step["target"])
        return True

    register_act_handler("jump", handle_jump)
