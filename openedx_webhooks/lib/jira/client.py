# -*- coding: utf-8 -*-
"""
JIRA client instance.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from base64 import b64decode
import os

from jira import JIRA

try:
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv())
except ImportError:  # pragma: no cover
    pass


_server = os.environ.get('JIRA_SERVER')
_oauth_info = dict(
    access_token=os.environ.get('JIRA_ACCESS_TOKEN'),
    access_token_secret=os.environ.get('JIRA_ACCESS_TOKEN_SECRET'),
    consumer_key=os.environ.get('JIRA_OAUTH_CONSUMER_KEY'),
    key_cert=b64decode(os.environ.get('JIRA_OAUTH_PRIVATE_KEY')),
)

# (jira.JIRA): An authenticated JIRA API client session
jira_client = JIRA(_server, oauth=_oauth_info)
