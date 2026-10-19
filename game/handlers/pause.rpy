init python:
    def handle_pause(step, chars):
        dur = step.get("duration", 1.0)
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 1.0
        checkpoint_data = renpy.pause(dur, checkpoint=False)
        renpy.checkpoint(checkpoint_data, hard=True)
        return PlaybackActionResult.continue_()

    register_act_handler("pause", handle_pause)
