# -*- coding: utf-8 -*-
# Copyright 2019 Green Valley Belgium NV
# NOTICE: THIS FILE HAS BEEN MODIFIED BY GREEN VALLEY BELGIUM NV IN ACCORDANCE WITH THE APACHE LICENSE VERSION 2.0
# Copyright 2018 GIG Technology NV
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
# @@license_version:1.6@@

import logging

from google.appengine.ext import ndb

from framework.plugin_loader import get_config
from plugins.intercom_support import models
from plugins.intercom_support.models import IntercomConversation, RogerthatConversation
from plugins.intercom_support.plugin_consts import NAMESPACE


def get_rogerthat_api_key():
    return get_config(NAMESPACE)["rogerthat_api_key"]


def get_intercom_api_key():
    return get_config(NAMESPACE)["intercom_api_access_key"]


def get_intercom_webhook_hub_secret():
    return get_config(NAMESPACE)["intercom_webhook_hub_secret"]


def get_chat_for_user(username):
    # type: (unicode) -> RogerthatConversation
    return RogerthatConversation.get_by_user(username)


@ndb.transactional()
def store_chat(intercom_user_id, chat_id, intercom_support_chat_id=None, intercom_support_message_id=None):
    logging.info('store_chat %s', locals())
    key = RogerthatConversation.create_key(intercom_user_id, chat_id)
    rc = key.get()
    if not rc:
        rc = RogerthatConversation(key=key)
    rc.intercom_support_chat_id = intercom_support_chat_id
    if intercom_support_message_id:
        rc.intercom_support_message_id = intercom_support_message_id
    rc.put()
    if intercom_support_chat_id:
        ic = IntercomConversation(
            key=models.IntercomConversation.create_key(intercom_user_id, intercom_support_chat_id))
        ic.rogerthat_chat_id = chat_id
        ic.put()
    if intercom_support_message_id:
        ic = models.IntercomConversation(
            key=IntercomConversation.create_key(intercom_user_id, intercom_support_message_id))
        ic.rogerthat_chat_id = chat_id
        ic.put()
