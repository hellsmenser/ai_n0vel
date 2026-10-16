init python:
    def handle_pause(step, chars):
        dur = step.get("duration", 1.0)
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 1.0
        renpy.pause(dur)
        return False

    register_act_handler("pause", handle_pause)
