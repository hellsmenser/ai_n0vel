init python:
    def handle_animate(step, chars):
        target = step.get("target")
        effect = step.get("effect")
        if effect == "shake":
            from renpy.display.motion import ATLTransform
            shake = ATLTransform(xoffset=10, yoffset=0, time=0.05, repeat=True, bounce=True)
            renpy.show(target, at_list=[shake])
        return False

    register_act_handler("animate", handle_animate)
