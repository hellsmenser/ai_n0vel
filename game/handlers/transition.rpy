init python:
    from renpy.display.transition import Fade, Dissolve


    def handle_transition(step, chars):
        eff_name = step.get("effect", "fade").lower()
        if eff_name == "fade":
            # Ren'Py instantiates transition factories with old/new widgets.
            # Passing an already-created Fade (a MultipleTransition) makes it
            # get called again and raises "MultipleTransition is not callable".
            eff = renpy.curry(Fade)(0.5, 0.0, 0.5)
        elif eff_name == "dissolve":
            eff = renpy.curry(Dissolve)(0.5)
        else:
            return PlaybackActionResult.continue_()
        renpy.with_statement(eff)
        return PlaybackActionResult.continue_()

    register_act_handler("transition", handle_transition)
