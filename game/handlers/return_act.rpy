init python:
    def handle_return(step, chars):
        return True
    register_act_handler("return", handle_return)
