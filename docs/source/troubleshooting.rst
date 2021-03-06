Troubleshooting
===============

"Your account has been locked due to too many failed login attempts"
--------------------------------------------------------------------

This feature is provided by `django-axes <https://django-axes.readthedocs.io>`_. You can reset account lockouts using the command ``docker-compose exec web python manage.py axes_reset`` while CalcUS is running. Alternatively, you can reset individual lockouts by ip (``docker-compose exec web python manage.py axes_reset_ip <ip>``) or by username (``docker-compose exec web python manage.py axes_reset_username <username>``).

By default, 5 login attempts are tolerated before locking the account. The lockout will be cleared after one hour. These values can be changed in ``calcus/settings.py`` by modifying ``AXES_FAILURE_LIMIT`` and ``AXES_COOLOFF_TIME``. View `Django-axes' documentation <https://django-axes.readthedocs.io>`_ for more details.

Unable to connect/This site can't be reached
--------------------------------------------

If you are running CalcUS on your own computer, make sure to use the address `http://0.0.0.0:8080/ <http://0.0.0.0:8080/>`_ and *not* 0.0.0.0:**8000** as the Django logs say. While the Django server does listen on port 8000, it is not directly accessible; you must connect to Nginx on port 8080 in order to use CalcUS.


"Your connection to this site is not secure"
--------------------------------------------

This message may appear in your browser when accessing CalcUS. This is due to the fact that CalcUS does not use SSL or TLS encryption by default. In order to do so, an encryption certificate must be generated by a certificate authority. This must be done for each "server", meaning *each instance of CalcUS*. If you desire to have encryption on your instance of CalcUS, you must thus perform this process yourself. Also know that it is not trivial to add encryption to websites which are not public (*i.e.* websites on intranets or private networks). We however do not recommend exposing a CalcUS instance to the whole internet.

Gaussian 16 calculations crash without any error message
--------------------------------------------------------

If you notice that Gaussian 16 calculations crash right after the structure printout in the log file, you might need to add ``PGI_FASTMATH_CPU=sandybridge`` in your .env file.

