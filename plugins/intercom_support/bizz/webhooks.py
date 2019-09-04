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
import re
import uuid
from HTMLParser import HTMLParser

from framework.utils import try_or_defer
from plugins.intercom_support import get_rogerthat_api_key, store_chat, models
from plugins.rogerthat_api.api import messaging as messaging_api
from plugins.rogerthat_api.to.messaging import AnswerTO, AttachmentTO, Message


class IntercomConversationParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.__text = []
        self.__article_get_text = False
        self.__article_link = None
        self.__articles = {}
        self.__recording = False
        self.__image_recording = False
        self.__images = []

    def handle_data(self, data):
        if self.__recording:
            text = data.strip()
            if len(text) > 0:
                text = re.sub('[ \t\r\n]+', ' ', text)
                self.__text.append(text + ' ')
        if self.__article_get_text:
            self.__articles[self.__article_link] = data
            self.__article_get_text = False
            self.__article_link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.__recording:
            if tag == 'br':
                self.__text.append('\n\n')
        if tag == 'p':
            self.__recording = True
        if tag == 'a' and attrs.get('data-link-type') == 'educate.article':
            self.__article_link = attrs['href']
        if tag == 'div' and attrs['class'] == 'intercom-interblocks-link-title':
            self.__article_get_text = True
        if tag == 'div' and attrs['class'] == 'intercom-container':
            self.__image_recording = True
        if tag == 'img' and self.__image_recording:
            self.__images.append(attrs['src'])

    def handle_endtag(self, tag):
        if tag == 'p':
            self.__recording = False

    def text(self):
        return '\n\n'.join(self.__text).strip()

    def articles(self):
        return self.__articles

    def images(self):
        return self.__images


def _get_intercom_conversation(payload):
    # type: (dict) -> models.IntercomConversation
    intercom_support_message_id = payload['data']['item']['conversation_message']['id']
    user_id = payload['data']['item']['user']['user_id']
    if not user_id:
        logging.info('intercom user_id not set, ignoring conversation')
        return
    # Check if we know this chat?
    ic = models.IntercomConversation.create_key(user_id, intercom_support_message_id).get()
    if not ic:
        logging.info('IntercomConversation not found, ignoring')
    return ic


def conversation_user_created(payload):
    intercom_support_chat_id = payload['data']['item']['id']
    ic = _get_intercom_conversation(payload)
    if not ic:
        return
    try_or_defer(store_chat, ic.user_id, ic.rogerthat_chat_id,
                 intercom_support_message_id=ic.message_id,
                 intercom_support_chat_id=intercom_support_chat_id)


def conversation_admin_replied(payload):
    try_or_defer(_conversation_admin_replied, payload)


def _conversation_admin_replied(payload):
    ic = _get_intercom_conversation(payload)
    if not ic:
        return

    # Get message to be forwarded
    for part in payload['data']['item']['conversation_parts']['conversation_parts']:
        if part['part_type'] == 'comment':
            break
    else:
        logging.info('Nothing to forward')
        return

    # Parse message
    try:
        parser = IntercomConversationParser()
        parser.feed(part['body'])
        parser.close()
        message = parser.text()
    except:
        logging.exception('Failed to parse intercom message')
        message = part['body']
    answers = []
    for article_link, article_title in parser.articles().iteritems():
        answers.append(AnswerTO(id=unicode(uuid.uuid4()),
                                type=u'button',
                                caption=article_title,
                                action=article_link,
                                ui_flags=0,
                                color=None))
    attachments = []
    for image in parser.images():
        attachments.append(AttachmentTO(content_type=AttachmentTO.CONTENT_TYPE_IMG_PNG,
                                        download_url=image,
                                        name=(unicode(uuid.uuid4())),
                                        size=0))

    # Add attachments
    for attachment in part['attachments']:
        content_type = attachment['content_type']
        if content_type not in AttachmentTO.CONTENT_TYPES:
            logging.error('Skipped attachment %s, due to incompatible content type' % content_type)
            continue
        attachments.append(AttachmentTO(name=unicode(uuid.uuid4()),
                                        content_type=content_type,
                                        download_url=attachment['url'],
                                        size=attachment['filesize']))

    # Forward the message to the Rogerthat app
    api_key = get_rogerthat_api_key()
    parent_key = ic.rogerthat_chat_id
    alert_flags = Message.ALERT_FLAG_VIBRATE
    messaging_api.send_chat_message(api_key, parent_key, message, answers=answers, attachments=attachments, sender=None,
                                    priority=None, sticky=False, tag=None, alert_flags=alert_flags, json_rpc_id=None)
