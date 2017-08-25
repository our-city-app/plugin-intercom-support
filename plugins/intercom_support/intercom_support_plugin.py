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

import logging

from framework.plugin_loader import Plugin, get_plugin
from framework.utils.plugins import Handler
from plugins.intercom_support import intercom_webhooks, rogerthat_callbacks
from plugins.rogerthat_api.rogerthat_api_plugin import RogerthatApiPlugin


class IntercomSupportPlugin(Plugin):
    def __init__(self, configuration):
        super(IntercomSupportPlugin, self).__init__(configuration)
        rogerthat_api_plugin = get_plugin('rogerthat_api')
        assert isinstance(rogerthat_api_plugin, RogerthatApiPlugin)
        rogerthat_api_plugin.subscribe('messaging.poke', rogerthat_callbacks.messaging_poke)
        rogerthat_api_plugin.subscribe('messaging.new_chat_message', rogerthat_callbacks.messaging_new_chat_message)

    def get_handlers(self, auth):
        logging.debug("Adding handlers")
        if auth == Handler.AUTH_UNAUTHENTICATED:
            logging.debug("Adding unauthenticated headers")
            yield Handler('/plugins/intercom-support/intercom-webhook', intercom_webhooks.IntercomWebhookHandler)