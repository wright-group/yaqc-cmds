### Curve Fitting - Fast and Simple

from scipy import optimize
from numpy import *

class Parameter:
    def __init__(self, value):
            self.value = value

    def set(self, value):
            self.value = value

    def __call__(self):
            return self.value

def fit(function, parameters, y, x = None):
    def f(params):
        i = 0
        for p in parameters:
            p.set(params[i])
            i += 1
        return y - function(x)

    if x is None: x = arange(y.shape[0])
    p = [param() for param in parameters]
    optimize.leastsq(f, p)

### Gaussian Auto-Guess
def Gauss_guess(xi,yi):
    '''
    gives a good initial guess for a guassian of the form
    amp*exp(-(t-mean)**2/(2*width**2)) + y0
    '''
    ystdev = std(yi)
    baseline = []
    for i in yi:
        if abs(i)<= 3*ystdev:
            baseline.append(i)
    y0 = average(baseline)
    yi = [i-y0 for i in yi]
    mean = sum(multiply(xi,yi))/sum(yi)
    width = sqrt(abs(sum((xi-mean)**2*data)/sum(data))
    amp = max(yi)
    return [mean,width,amp,y0]



### Example fitting ###########################################################

if False:
    # Set initial parameters
    mu = Parameter(6.5)
    sigma = Parameter(3.211)
    height = Parameter(5.32)
    offset = Parameter (0)

    # Define function
    def f(x):
        return offset() + height() * exp(-((x-mu())/sigma())**2)

    # Fit!!
    fit(f, [mu,sigma,height,offset], data)