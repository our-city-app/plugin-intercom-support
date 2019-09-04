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

import hashlib
import hmac
import json
import logging

import webapp2

from plugins.intercom_support import get_intercom_webhook_hub_secret
from plugins.intercom_support.bizz.webhooks import conversation_user_created, conversation_admin_replied

# See https://developers.intercom.com/reference#topics
INTERCOM_HANDLERS = {
    'conversation.user.created': conversation_user_created,
    'conversation.admin.replied': conversation_admin_replied,
}


class IntercomWebhookHandler(webapp2.RequestHandler):
    def post(self):
        signature = self.request.headers['X-Hub-Signature']
        body = self.request.body
        calculated_signature = 'sha1=%s' % hmac.new(get_intercom_webhook_hub_secret().encode(),
                                                    body, hashlib.sha1).hexdigest()
        if signature != calculated_signature:
            logging.error("""Failed to authenticate incoming webhook!
signature: %(signature)s
calculated_signature: %(calculated_signature)s""" % locals())
            return

        logging.info('Incomming call from intercom: %s' % body)

        payload = json.loads(body)
        topic = payload['topic']
        handler = INTERCOM_HANDLERS.get(topic)
        if handler:
            handler(payload)
        else:
            logging.debug('No handler found for topic \'%s\'' % topic)
