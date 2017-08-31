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

import hashlib
import hmac
import json
import logging
import re
import uuid
from HTMLParser import HTMLParser

import webapp2

from plugins.intercom_support import get_rogerthat_api_key, store_chat, try_or_defer, get_intercom_webhook_hub_secret, \
    models
from plugins.rogerthat_api.api import messaging as messaging_api
from plugins.rogerthat_api.to import messaging as messaging_to


class IntercomWebhookHandler(webapp2.RequestHandler):
    def post(self):
        signature = self.request.headers['X-Hub-Signature']
        body = self.request.body
        calculated_signature = 'sha1=%s' % hmac.new(get_intercom_webhook_hub_secret().encode(),
                                                    body, hashlib.sha1).hexdigest()
        if signature != calculated_signature:
            logging.error("""Failed to authenticate incomming webhook!
signature: %(signature)s
calculated_signature: %(calculated_signature)s""" % locals())
            return

        logging.info("Incomming call from intercom: %s" % body)

        payload = json.loads(body)
        topic = payload["topic"]
        handler = globals().get(topic.replace('.', "_"))
        if handler:
            handler(payload)
        else:
            logging.warn("No handler found for topic '%s'" % topic)


def conversation_user_created(payload):
    intercom_support_chat_id = payload["data"]["item"]["id"]
    intercom_support_message_id = payload["data"]["item"]["conversation_message"]["id"]
    user_id = payload["data"]["item"]["user"]["user_id"]
    ic = models.IntercomConversation.create_key(user_id, intercom_support_message_id).get()
    rogerthat_chat_id = ic.rogerthat_chat_id
    try_or_defer(store_chat, user_id, rogerthat_chat_id, intercom_support_message_id=intercom_support_message_id,
                 intercom_support_chat_id=intercom_support_chat_id)


def conversation_admin_replied(payload):
    intercom_support_chat_id = payload["data"]["item"]["conversation_message"]["id"]
    user_id = payload["data"]["item"]["user"]["user_id"]

    # Check if we know this chat?
    ic = models.IntercomConversation.create_key(user_id, intercom_support_chat_id).get()
    if not ic:
        logging.info("Ignoring converstation.")
        return

    # Get message to be forwarded
    for part in payload["data"]["item"]["conversation_parts"]["conversation_parts"]:
        if part["part_type"] == "comment":
            break
    else:
        logging.info("Nothing to forward")
        return

    # Parse message
    try:
        parser = IntercomConversationParser()
        parser.feed(part["body"])
        parser.close()
        message = parser.text()
    except:
        logging.exception("Failed to parse intercom message")
        message = part["body"]
    answers = list()
    for article_link, article_title in parser.articles().iteritems():
        a = messaging_to.AnswerTO()
        a.id = unicode(uuid.uuid4())
        a.caption = article_title
        a.action = article_link
        answers.append(a)
    attachments = list()
    for image in parser.images():
        a = messaging_to.AttachmentTO()
        a.content_type = messaging_to.AttachmentTO.CONTENT_TYPE_IMG_PNG
        a.download_url = image
        a.name = unicode(uuid.uuid4())
        a.size = 0
        attachments.append(a)

    # Add attachments
    for attachment in part["attachments"]:
        content_type = attachment["content_type"]
        if content_type not in messaging_to.AttachmentTO.CONTENT_TYPES:
            logging.error("Skipped attachment %s, due to incompatible content type" % content_type)
            continue
        a = messaging_to.AttachmentTO()
        a.name = unicode(uuid.uuid4())
        a.content_type = content_type
        a.download_url = attachment["url"]
        a.size = attachment["filesize"]
        attachments.append(a)

    # Forward the message to the Rogerthat app
    api_key = get_rogerthat_api_key()
    parent_key = ic.rogerthat_chat_id
    messaging_api.send_chat_message(api_key, parent_key, message, answers=answers, attachments=attachments, sender=None,
                                    priority=None,
                                    sticky=False, tag=None, alert_flags=messaging_to.Message.ALERT_FLAG_VIBRATE,
                                    json_rpc_id=None)


class IntercomConversationParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.__text = []
        self.__article_get_text = False
        self.__article_link = None
        self.__articles = dict()
        self.__recording = False
        self.__image_recording = False
        self.__images = []

    def handle_data(self, data):
        if self.__recording:
            text = data.strip()
            if len(text) > 0:
                text = re.sub("[ \t\r\n]+", " ", text)
                self.__text.append(text + " ")
        if self.__article_get_text:
            self.__articles[self.__article_link] = data
            self.__article_get_text = False
            self.__article_link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.__recording:
            if tag == "br":
                self.__text.append('\n\n')
        if tag == "p":
            self.__recording = True
        if tag == "a" and attrs["data-link-type"] == "educate.article":
            self.__article_link = attrs["href"]
        if tag == "div" and attrs["class"] == "intercom-interblocks-link-title":
            self.__article_get_text = True
        if tag == "div" and attrs["class"] == "intercom-container":
            self.__image_recording = True
        if tag == "img" and self.__image_recording:
            self.__images.append(attrs["src"])

    def handle_endtag(self, tag):
        if tag == "p":
            self.__recording = False

    def text(self):
        return "\n\n".join(self.__text).strip()

    def articles(self):
        return self.__articles

    def images(self):
        return self.__images
