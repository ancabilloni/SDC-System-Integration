
GAS_DENSITY = 2.858
ONE_MPH = 0.44704


class Controller(object):
    def __init__(self, *args, **kwargs):
        # TODO: Implement
        # pass
        self.throttle = 1
        self.brake = 0
        self.steer = 0

    # def control(self, *args, **kwargs):
    #     # TODO: Change the arg, kwarg list to suit your needs
    #     # Return throttle, brake, steer
    #     return 1., 0., 0.

    # def control(self):
    #     # TODO: Change the arg, kwarg list to suit your needs
    #     # Return throttle, brake, steer
    #     self.throttle = 1
    #     self.brake = 0
    #     self.steer = 0
    #     # return 1., 0., 0.
