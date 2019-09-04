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

from framework.plugin_loader import Plugin, get_plugin
from framework.utils.plugins import Handler
from plugins.intercom_support import intercom_webhooks, rogerthat_callbacks
from plugins.intercom_support.bizz import intercom_api
from plugins.rogerthat_api.rogerthat_api_plugin import RogerthatApiPlugin


class IntercomSupportPlugin(Plugin):
    def __init__(self, configuration):
        super(IntercomSupportPlugin, self).__init__(configuration)
        rogerthat_api_plugin = get_plugin('rogerthat_api')
        assert isinstance(rogerthat_api_plugin, RogerthatApiPlugin)
        rogerthat_api_plugin.subscribe('messaging.poke', rogerthat_callbacks.messaging_poke, trigger_only=True)
        rogerthat_api_plugin.subscribe('messaging.new_chat_message', rogerthat_callbacks.messaging_new_chat_message,
                                       trigger_only=True)

    def get_handlers(self, auth):
        if auth == Handler.AUTH_UNAUTHENTICATED:
            yield Handler('/plugins/intercom-support/intercom-webhook', intercom_webhooks.IntercomWebhookHandler)

    def upsert_user(self, user_id, name, email, phone):
        return intercom_api.upsert_user(user_id, name, email, phone)

    def get_user(self, id=None, user_id=None, email=None):
        return intercom_api.get_user(id, user_id, email)

    def send_message(self, from_, message, message_type='inapp', subject=None, template='plain', to=None):
        return intercom_api.send_message(from_, message, message_type, subject, template, to)

    def tag_users(self, tag_name, users):
        """
        Args:
            tag_name (unicode): tag name
            users: (list[dict]): List of user objects with either id, user_id or email as properties.
        Examples:
            >>> IntercomSupportPlugin().tag_users('sample_tag', [{'email': 'test@example.com'}, {'user_id': 'test'}])
        Returns:
            Tag
        """
        return intercom_api.tag_users(tag_name, users)
