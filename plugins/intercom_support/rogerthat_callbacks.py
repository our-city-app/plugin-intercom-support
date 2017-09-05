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

from plugins.intercom_support import intercom_post, models, try_or_defer, store_chat
from plugins.rogerthat_api.api import messaging as messaging_api
from plugins.rogerthat_api.to import MemberTO
from plugins.rogerthat_api.to.messaging import ChatFlags


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


def messaging_poke(rt_settings, id_, service_identity, user_details, tag, **kwargs):
    if tag != 'intercom_support_new_chat':
        logging.info('Ignoring poke callback with tag "%s"' % tag)
        return

    message = None
    context = kwargs["context"]
    json_rpc_id = str(uuid.uuid4())

    try_or_defer(_start_new_chat, rt_settings, service_identity, user_details, message, context, json_rpc_id,
                 _target="default")


def messaging_new_chat_message(rt_settings, id_, tag, **kwargs):
    if tag != 'intercom_support_chat':
        logging.info('Ignoring new_chat_message callback with tag "%s"' % tag)
        return

    user_id = kwargs['sender']['email']
    user_name = kwargs['sender']['name']
    chat_id = kwargs['parent_message_key']
    message = kwargs['message']
    attachments = kwargs['attachments']

    rc = models.RogerthatConversation.create_key(user_id, chat_id).get()
    if not rc:
        logging.error('No reference found in datastore for chat "%s"' % chat_id)
        return

    intercom_support_chat_id = rc.intercom_support_chat_id

    if intercom_support_chat_id:
        intercom_post("conversations/%s/reply" % intercom_support_chat_id,
                      dict(type='user', message_type='comment', user_id=user_id,
                           body=message, attachment_urls=[a["download_url"] for a in attachments]))
    else:
        if rc.intercom_support_message_id:
            deferred.defer(messaging_new_chat_message, rt_settings, id_, _countdown=1, **kwargs)
        else:
            intercom_user = intercom_post("users", dict(user_id=user_id, name=user_name))
            intercom_conversation = intercom_post("messages", {"from": intercom_user, "body": message})
            intercom_support_message_id = intercom_conversation["id"]

            # Store the chat references
            try_or_defer(store_chat, user_id, chat_id, intercom_support_message_id)


def _start_new_chat(rt_settings, service_identity, user_details, message, context, json_rpc_id):
    # Start chat in rogerthat.
    api_key = rt_settings.api_key
    member = MemberTO()
    member.app_id = user_details[0]["app_id"]
    member.member = user_details[0]["email"]
    member.alert_flags = 0
    topic = "Support request"
    chat_id = messaging_api.start_chat(api_key, [member], topic, message or "Hello, how can we be of service?",
                                       service_identity=service_identity, tag="intercom_support_chat", context=context,
                                       flags=ChatFlags.ALLOW_PICTURE, description=message, default_sticky=True,
                                       json_rpc_id=json_rpc_id, )

    if message:
        # Start conversation in intercom
        intercom_user = intercom_post("users", dict(user_id=user_details["email"], name=user_details["name"]))
        intercom_conversation = intercom_post("messages", {"from": intercom_user, "body": message})
        intercom_support_message_id = intercom_conversation["id"]
    else:
        intercom_support_message_id = None

    # Store the chat references
    try_or_defer(store_chat, user_details[0]["email"], chat_id, intercom_support_message_id=intercom_support_message_id)
