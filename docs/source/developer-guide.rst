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

All the relevant tests should be ran before submitting a pull request.

To run the entire test suite, first start the development environment:

.. code-block:: console

        $ docker-compose -f test-compose.yml -f test-compose.override.yml up

Then, in another shell, run the tests:

.. code-block:: console

        $ docker-compose -f test-compose.yml -f test-compose.override.yml run web bash run_tests.sh

You may also run specific tests during the development process as such:

.. code-block:: console

        $ docker-compose -f test-compose.yml -f test-compose.override.yml run web python3 manage.py test frontend.test_...

Note that, despite our best efforts, integration tests (*i.e.* ``test_selenium.py`` and ``test_cluster.py``)are prone to giving variable outcomes. If a test fails and appears unrelated to changes you have made, try running the test again. Further debugging can make use of Virtual Network Computing (VNC). In particular, you can connect to the virtual machine running Selenium, and thus view exactly what is happening. To do so, connect with any VNC client to ``localhost`` and use the password ``secret``.

New functionalities must be minimally tested. When submitting your pull request, make sure that it contains at least a few tests that will fail if the functionality stops working. Depending on the nature of the functionality, integration tests or unit tests can be used. The main purpose of this is the ensure a certain stability of all the functionalities.

Bug fixes must also contain enough tests to ensure that the bug could not occur again unnoticed.

