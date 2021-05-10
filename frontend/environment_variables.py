import os

try:
    is_test = os.environ['CALCUS_TEST']
except:
    is_test = False

if is_test:
    CALCUS_SCR_HOME = os.environ['CALCUS_TEST_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_TEST_RESULTS_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_TEST_KEY_HOME']
else:
    CALCUS_SCR_HOME = os.environ['CALCUS_SCR_HOME']
    CALCUS_RESULTS_HOME = os.environ['CALCUS_RESULTS_HOME']
    CALCUS_KEY_HOME = os.environ['CALCUS_KEY_HOME']

docker = False
try:
    a = os.environ["CALCUS_DOCKER"]
except KeyError:
    pass
else:
    if a.lower() == "true":
        docker = True

PAL = os.environ['OMP_NUM_THREADS'][0]
STACKSIZE = os.environ['OMP_STACKSIZE']
if STACKSIZE.find("G") != -1:
    STACKSIZE = int(STACKSIZE.replace('G', ''))*1024
elif STACKSIZE.find("M") != -1:
    STACKSIZE = int(STACKSIZE.replace('M', ''))

MEM = int(PAL)*STACKSIZE
EBROOTORCA = os.environ['EBROOTORCA']
