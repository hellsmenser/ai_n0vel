init python:
    def handle_jump(step, chars):
        return PlaybackActionResult.goto(step["target"])

    register_act_handler("jump", handle_jump)
