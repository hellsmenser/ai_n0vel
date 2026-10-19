init python:
    def handle_return(step, chars):
        return PlaybackActionResult.scene_end()
    register_act_handler("return", handle_return)
