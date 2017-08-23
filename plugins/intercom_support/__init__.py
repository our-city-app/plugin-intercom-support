# -*- coding: utf-8 -*-
# Copyright 2017 GIG Technology NV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# @@license_version:1.3@@

import json
import logging

from google.appengine.api import urlfetch
from google.appengine.ext import ndb, deferred

from framework.plugin_loader import get_config
from mcfw.consts import DEBUG
from plugins.intercom_support.plugin_consts import NAMESPACE

def get_rogerthat_api_key():
    return get_config(NAMESPACE)["rogerthat_api_key"]

def get_intercom_api_key():
    return get_config(NAMESPACE)["intercom_api_access_key"]

def get_intercom_webhook_hub_secret():
    return get_config(NAMESPACE)["intercom_webhook_hub_secret"]

def intercom_post(resource, payload):
    api_key = get_intercom_api_key()
    body = json.dumps(payload)
    headers = {"Content-Type": "application/json", "Accept": "application/json",
               "Authorization": "Bearer %s" % api_key}
    logging.info("""POST %s HTTP/1.1
Host: api.intercom.io
Content-Type: application/json
Accept: application/json
Authorization: Bearer %s

%s""" % (resource, api_key, body))
    result = urlfetch.fetch(
        url='https://api.intercom.io/%s' % resource,
        payload=body,
        method=urlfetch.POST,
        headers=headers)
    logging.info("""
HTTP/1.1 %s OK
%s

%s
""" % (result.status_code, "\n".join(("%s: %s" % (k,v) for k,v in result.headers.iteritems())),
       result.content))
    if result.status_code != 200:
        raise RuntimeError("Intercom api request failed with status %s.\n%s" % (result.status_code, result.content))
    return json.loads(result.content)

def try_or_defer(method, *args, **kwargs):
    try:
        method(*args, **kwargs)
    except:
        deferred.defer(method, *args, **kwargs)

@ndb.transactional()
def store_chat(user_id, chat_id, intercom_support_chat_id=None, intercom_support_message_id=None):
    key = models.RogerthatConversation.create_key(user_id, chat_id)
    rc = key.get()
    if not rc:
        rc = models.RogerthatConversation(key=key)
    rc.intercom_support_chat_id = intercom_support_chat_id
    if intercom_support_message_id:
        rc.intercom_support_message_id = intercom_support_message_id
    rc.put()
    if intercom_support_chat_id:
        ic = models.IntercomConversation(key=models.IntercomConversation.create_key(user_id, intercom_support_chat_id))
        ic.rogerthat_chat_id = chat_id
        ic.put()
    if intercom_support_message_id:
        ic = models.IntercomConversation(key=models.IntercomConversation.create_key(user_id, intercom_support_message_id))
        ic.rogerthat_chat_id = chat_id
        ic.put()
