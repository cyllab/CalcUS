Developer Guide
===============

Contributing
------------
Contributions to the project in the form of feedback or pull requests are welcome. For code contributions, please make sure to provide good quality code with similar formatting as the rest of the project. Notably, this means:

* Variable names and comments should be in English
* Use tabs for indentation
* Use proper whitespace (for example, after commas)
* Comment complex or unintuitive lines of code

Tests
-----

All the relevant tests should be ran before submitting a pull request. You must at least run the unit tests (see below), as they are very fast and reliable. Integration tests can also be used, especially when modifications to the web frontend are done.

To run the entire test suite, first start the development environment:

.. code-block:: console

        $ ./start_test.sh

Then, in another shell, run the tests:

.. code-block:: console

        $ ./run_tests.sh

You may also run specific tests during the development process as such:

.. code-block:: console

        $ docker-compose -f test-compose.yml -f test-compose.override.yml run web python3 manage.py test frontend.test_...

Note that, despite our best efforts, integration tests (*i.e.* ``test_selenium.py`` and ``test_cluster.py``) are prone to giving variable outcomes. If a test fails and appears unrelated to changes you have made, try running the test again. Further debugging can make use of Virtual Network Computing (VNC). In particular, you can connect to the virtual machine running Selenium, and thus view exactly what is happening. To do so, connect with any VNC client to ``localhost`` and use the password ``secret``.

New functionalities must be minimally tested. When submitting your pull request, make sure that it contains at least a few tests that will fail if the functionality stops working. Depending on the nature of the functionality, integration tests or unit tests can be used. The main purpose of this is the ensure a certain stability of all the functionalities.

Bug fixes must also contain enough tests to ensure that the bug could not occur again unnoticed. You have the liberty of choose either unit tests, integration tests or both.

As many tests require the output files of quantum chemistry packages, the required files have been generated and added to the repository under ``frontend/tests/cache/``. As such, you should not need to have any quantum chemistry package to run the tests. If your tests require additional output files, please add them to your pull request. By default, if no cached output file is found, CalcUS will attempt to run the requested calculation. The output file will automatically be added to the cache.

**Unit tests:**

- ``frontend/test_calculations.py``
- ``frontend/test_views.py``
- ``frontend/test_xyz.py``
- ``frontend/test_units.py``
- ``frontend/test_md5.py``
- ``frontend/test_fingerprint.py``

**Integration tests:**

- ``frontend/test_selenium.py``
- ``frontend/test_cluster.py`` (disabled in CI)

