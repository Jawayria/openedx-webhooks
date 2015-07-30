Webhooks for `Open edX`_, integrating `JIRA`_ and `Github`_,
designed to be deployed onto `Heroku`_.

|build-status| |coverage-status| |docs|

Tests::

    $ pip install -r dev-requirements.txt
    $ py.test --cov=openedx_webhooks


.. _Open edX: http://openedx.org
.. _JIRA: https://openedx.atlassian.net
.. _Github: https://github.com/edx
.. _Heroku: http://heroku.com
.. |build-status| image:: https://travis-ci.org/edx/openedx-webhooks.svg?branch=master
   :target: https://travis-ci.org/edx/openedx-webhooks
.. |coverage-status| image:: https://coveralls.io/repos/edx/openedx-webhooks/badge.png
   :target: https://coveralls.io/r/edx/openedx-webhooks
.. |docs| image:: https://readthedocs.org/projects/openedx-webhooks/badge/?version=latest
   :target: http://openedx-webhooks.readthedocs.org/en/latest/
   :alt: Documentation badge
