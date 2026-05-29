import glob
import os
from shutil import rmtree

for d in glob.glob("frontend.test_calculations.GaussianCalculationTests*/"):
    if not os.path.isfile(os.path.join(d, "calc.log")):
        print(d)
        # rmtree(d)
