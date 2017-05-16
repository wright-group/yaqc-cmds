class PoyntingCorrectionDevice(object):

    def __init__(self):
        raise NotImplementedError
    
    def load_curve(self, path):
        raise NotImplementedError
    def get_position(self):
        raise NotImplementedError
    def set_position(self,color):
        raise NotImplementedError
    def is_busy(self):
        raise NotImplementedError
    def wait_until_still(self):
        raise NotImplementedError

    # Methods for phi
    def get_phi(self):
        raise NotImplementedError
    def move_rel_phi(self, amount):
        raise NotImplementedError
    def move_abs_phi(self, position):
        raise NotImplementedError
    def home_phi(self):
        raise NotImplementedError

    # Methods for theta
    def get_theta(self):
        raise NotImplementedError
    def move_rel_theta(self, amount):
        raise NotImplementedError
    def move_abs_theta(self, position):
        raise NotImplementedError
    def home_theta(self):
        raise NotImplementedError
