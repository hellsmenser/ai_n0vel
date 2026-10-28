init python:
    SHOW_SLOT_XALIGN = {
        "far_left": 0.0,
        "left": 0.25,
        "center": 0.5,
        "right": 0.75,
        "far_right": 1.0,
    }

    def show_transform_properties(tf):
        xalign = SHOW_SLOT_XALIGN[tf["slot"]] if "slot" in tf else tf.get("xalign", 0.5)
        return {
            "xalign": xalign,
            "yalign": tf.get("yalign", 1.0),
            "alpha": tf.get("alpha", 1.0),
            "xzoom": -1.0 if tf.get("flip") else 1.0,
        }

    def handle_show(step, chars):
        target = step["target"]
        tf = step.get("transform")
        if tf:
            t = renpy.display.transform.Transform(**show_transform_properties(tf))
            renpy.show(target, at_list=[t])
        else:
            renpy.show(target)
        return PlaybackActionResult.continue_()

    register_act_handler("show", handle_show)
