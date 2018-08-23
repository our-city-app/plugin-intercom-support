# -*- coding: utf-8 -*-  # Copyright 2017 GIG Technology NV
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
import uuid

from google.appengine.ext import deferred

from framework.utils import try_or_defer
from intercom import ResourceNotFound
from mcfw.rpc import parse_complex_value
from plugins.intercom_support import models, store_chat, get_chat_for_user
from plugins.intercom_support.bizz import intercom_api
from plugins.intercom_support.util import get_username
from plugins.rogerthat_api.api import messaging as messaging_api
from plugins.rogerthat_api.to import MemberTO, UserDetailsTO
from plugins.rogerthat_api.to.messaging import ChatFlags, Message


def log_and_parse_user_details(user_details):
    # type: (dict) -> UserDetailsTO
    user_detail = user_details[0] if isinstance(user_details, list) else user_details
    logging.debug('Current user: %(email)s:%(app_id)s', user_detail)
    return parse_complex_value(UserDetailsTO, user_detail, False)


def messaging_flow_member_result(rt_settings, id_, service_identity, user_details, tag, **kwargs):
    if tag != 'intercom_support_new_chat':
        logging.info('Ignoring flow_member_result callback with tag "%s"' % tag)
        return

    def get_step(name):
        for step in kwargs.get('steps', []):
            if step["step_id"] == "message_%s" % name and step["answer_id"] == "positive":
                return step

    step = get_step("message")
    if not step:
        logging.error("Required step 'message' not found in the flow result. Aborting.")
        return

    message = step["form_result"]["result"]
    context = kwargs["context"]
    json_rpc_id = kwargs["message_flow_run_id"]

    deferred.defer(_start_new_chat, rt_settings, service_identity, user_details, message, context, json_rpc_id)


def messaging_poke(rt_settings, id_, params, response):
    tag = params['tag']
    context = params['context']
    service_identity = params['service_identity']
    user_details = params['user_details']
    if tag != 'intercom_support_new_chat':
        logging.info('Ignoring poke callback with tag \'%s\'' % tag)
        return

    message = None
    json_rpc_id = str(uuid.uuid4())

    try_or_defer(_start_new_chat, rt_settings, service_identity, user_details, message, context, json_rpc_id,
                 _target='default')


def messaging_new_chat_message(rt_settings, id_, params, response):
    tag = params['tag']
    if tag != 'intercom_support_chat':
        logging.info('Ignoring new_chat_message callback with tag "%s"' % tag)
        return

    user_detail = log_and_parse_user_details(params['sender'])
    user_name = params['sender']['name']
    chat_id = params['parent_message_key']
    message = params['message']
    attachments = params['attachments']

    intercom_user = intercom_api.upsert_user(get_username(user_detail), user_name)

    rc = models.RogerthatConversation.create_key(intercom_user.user_id, chat_id).get()
    if not rc:
        logging.error('No reference found in datastore for chat "%s"' % chat_id)
        return

    if rc.intercom_support_chat_id:
        attachment_urls = [a['download_url'] for a in attachments]
        try:
            intercom_api.reply(rc.intercom_support_chat_id, 'user', intercom_user.id, 'comment', message,
                               attachment_urls)
            return
        except ResourceNotFound as e:
            logging.exception(e)
    conversation_message = intercom_api.send_message({'type': 'user', 'id': intercom_user.id}, message)
    conversation = find_conversation_by_message_id(conversation_message.id, intercom_user.id)
    # Store the chat references
    try_or_defer(store_chat, intercom_user.user_id, chat_id, conversation.id)


def find_conversation_by_message_id(message_id, user_id):
    conversations = intercom_api.list_conversations(user_id)
    for conversation in conversations:
        if conversation.conversation_message.id == message_id:
            return conversation


def _start_new_chat(rt_settings, service_identity, user_details, message, context, json_rpc_id):
    # Start chat in rogerthat.
    user_details = log_and_parse_user_details(user_details)
    member = MemberTO(app_id=user_details.app_id, member=user_details.email, alert_flags=0)
    if message:
        store_on_intercom = True
    else:
        message = 'Hello, how can we be of service?'
        store_on_intercom = False
    return _start_support_chat(rt_settings.api_key, service_identity, member, message, context, json_rpc_id,
                               store_on_intercom)


def _start_support_chat(api_key, service_identity, member, message, context, json_rpc_id, store_on_intercom,
                        intercom_user=None):
    topic = 'Support'
    chat_flags = ChatFlags.ALLOW_PICTURE | ChatFlags.NOT_REMOVABLE
    chat_id = messaging_api.start_chat(api_key, [member], topic, message,
                                       service_identity=service_identity, tag='intercom_support_chat', context=context,
                                       flags=chat_flags, description=message, default_sticky=True,
                                       json_rpc_id=json_rpc_id)

    if not intercom_user:
        intercom_user = intercom_api.upsert_user(get_username(member.member))
    # Don't store 'how can we be of service' messages in intercom yet
    if store_on_intercom:
        intercom_conversation = intercom_api.send_message({'type': 'user', 'id': intercom_user.id}, message)
        intercom_support_message_id = intercom_conversation.id
    else:
        intercom_support_message_id = None
    try_or_defer(store_chat, intercom_user.user_id, chat_id, intercom_support_message_id=intercom_support_message_id)
    return chat_id


def start_or_get_chat(api_key, service_identity, email, app_id, intercom_user, message):
    user_id = intercom_user.user_id
    conversation = get_chat_for_user(intercom_user.user_id)
    if conversation:
        logging.info('Found existing support chat %s for user %s', conversation.rogerthat_chat_id, user_id)
        return conversation.rogerthat_chat_id
    else:
        logging.info('Creating new support chat user %s', user_id)
        member = MemberTO(app_id=app_id, member=email, alert_flags=Message.ALERT_FLAG_SILENT)
        json_rpc_id = str(uuid.uuid4())
        return _start_support_chat(api_key, service_identity, member, message, None, json_rpc_id, False, intercom_user)
