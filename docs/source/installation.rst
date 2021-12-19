Installation
============

.. _installation:

Quickstart
----------

Firstly, install and configure Docker. On Linux, it is necessary to create a ``docker`` group if it does not already exist and to add yourself to it:

.. code-block:: console

        $ sudo groupadd docker
        $ sudo usermod -aG docker $USER
        $ newgrp docker

You will need to log out and log back in for the changes to be effective.

Then, clone the repository. In that repository, a file named ``.env`` will be needed to set the necessary environment variables. The script ``generate_env.py`` can be used to interactively create that file. Simply run it with the command ``python3 generate_env.py`` and answer the questions. When you will run CalcUS, a superuser account will be created with the username specified in the ``.env`` file. You can use this account as main account, but make sure to change the password if the server is accessible to others.

Also note that the ``.env`` contains **sensitive information** and should only be accessible by the server administrator.

Once the setup is complete launch CalcUS using ``start.sh`` (Linux/Mac) or ``start.bat`` (Windows). CalcUS is now available in your web browser at the address `0.0.0.0:8080 <http://0.0.0.0:8080>`_ (or equivalently `127.0.0.1:8080 <http://127.0.0.1:8080>`_ and `localhost:8080 <http://localhost:8080>`_). You might need to manually start the docker service if you've just installed it. It will start automatically at boot in the future.

Manual Configuration
--------------------
A typical ``.env`` will look something like this:

.. code-block::

        CALCUS_SECRET_KEY='de^%k+mia@*%fxl*n6zp^vghxnj4))30q9+h8e3_no-xb0*k40'
        CALCUS_GAUSSIAN=/home/user/softwares/g16
        CALCUS_ORCA=/home/user/softwares/orca
        CALCUS_OPENMPI=/home/user/.openmpi/
        CALCUS_XTB=/home/user/softwares/xtb/bin
        OMP_NUM_THREADS=8,1
        NUM_CPU=8
        OMP_STACKSIZE=1G
        USE_CACHED_LOGS=true
        POSTGRES_PASSWORD=7ho74kgeysywg0xw953rhpi5wg5tpg4oi1e1x1bbgwiruon6w5
        UID=1000
        GID=1000
        CALCUS_SU_NAME=SU
        CALCUS_PING_SATELLITE=True
        CALCUS_PING_CODE='vdv820s5i1j3eb6ztx5ldk6m0k5fbt9hefdr8mkttcz4fvm481'

``CALCUS_SECRET_KEY`` is the Django secret key that will be used as salt for cryptographic hash generation (`See more details in the Django documentation <https://docs.djangoproject.com/en/dev/ref/settings/#secret-key>`_). Note that it is not used to encrypt the users' password, so changing this key will not cause the loss of encrypted logins in the database. This should be generated during the setup, most conveniently by the ``generate_env.py`` script. Django also offers a function to generate secret keys:

.. code-block:: 

        from django.core.management.utils import get_random_secret_key  
        get_random_secret_key()

The next four variables are paths to directories containing the relevant software packages. If you do not have some of the other packages, the corresponding lines should not appear in the ``.env`` file nor in ``docker-compose.override.yml`` - this is automatically handled by the script ``generate_env.py``.

``OMP_NUM_THREADS`` and ``NUM_CPU`` specify the number of processors available for calculations (eight in the example above). For the moment, every calculation uses all available processors.

``OMP_STACKSIZE`` specifies the memory available per processor.

``USE_CACHED_LOGS`` is a flag regarding the use of calculation caching during the automated tests. If enabled, CalcUS will save the results of calculations performed during the tests in ``calcus/frontend/tests/cache``. When the tests are run again, CalcUS will detect input files that have been used in the past and directly yield the result without calculating it again.

``POSTGRES_PASSWORD`` is the password used for the PostgreSQL database. This information is sensitive and critical.

``UID`` and ``GID`` are the user and group ids used by the PostgreSQL service. These should correspond to the ids of the user running CalcUS in order to store the database with the correct ownership.

``CALCUS_SU_NAME`` is the username of the superuser account in CalcUS. At each startup, a command is ran to verify if this user exists. If it doesn't, it will be created with the password ``default``.

Building from source
--------------------

By default, CalcUS will parse the latest stable pre-built Docker image and run it. This acts a update mechanism and avoids having to build the Docker image yourself. If you want to modify CalcUS or just build the Docker image from code instead, you can do so with the following commands:

.. code-block:: console

   $ docker-compose -f dev-compose.yml -f docker-compose.override.yml build
   $ docker-compose -f dev-compose.yml -f docker-compose.override.yml up

To update CalcUS, you will need to first update the code using git (``git pull``), then rebuild with the commands above.

