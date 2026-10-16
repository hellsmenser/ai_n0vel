init python:
    from renpy.display.transition import Fade, Dissolve


    def handle_transition(step, chars):
        eff_name = step.get("effect", "fade").lower()
        if eff_name == "fade":
            eff = Fade(0.5, 0.0, 0.5)
        elif eff_name == "dissolve":
            eff = Dissolve(0.5, 0.0, 0.5)
        elif eff_name == "move":
            eff = Move(duration=0.5, enter=True, old=False)
        else:
            eff = Fade(0.5, 0.0, 0.5)
        renpy.transition(eff)
        return False

    register_act_handler("transition", handle_transition)
