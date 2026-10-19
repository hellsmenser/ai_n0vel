init python:
    def handle_show(step, chars):
        target = step["target"]
        tf = step.get("transform")
        if tf:
            t = renpy.display.transform.Transform(
                xalign=tf.get("xalign", 0.5),
                yalign=tf.get("yalign", 1.0),
                alpha=tf.get("alpha", 1.0),
                xzoom=-1.0 if tf.get("flip") else 1.0
            )
            renpy.show(target, at_list=[t])
        else:
            renpy.show(target)
        return PlaybackActionResult.continue_()

    register_act_handler("show", handle_show)
