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

import intercom
from intercom import ResourceNotFound
from intercom.client import Client
from plugins.intercom_support import get_intercom_api_key


def get_intercom_client():
    return Client(personal_access_token=get_intercom_api_key())


def upsert_user(user_id, name=None, email=None, phone=None):
    # type: (unicode, unicode) -> intercom.user.User
    client = get_intercom_client()
    try:
        user = client.users.find(user_id=user_id)
        return update_user_if_necessary(user, user_id, name, email, phone)
    except ResourceNotFound:
        if email:
            try:
                # try again by searching on email
                user = client.users.find(email=email)
                return update_user_if_necessary(user, user_id, name, email, phone)
            except ResourceNotFound:
                return create_user(user_id, name, email, phone)
        else:
            return create_user(user_id, name, email, phone)


def create_user(user_id, name, email, phone):
    logging.info('Creating new intercom user %s', locals())
    return get_intercom_client().users.create(user_id=user_id, name=name, email=email, phone=phone)


def update_user_if_necessary(user, user_id, name, email, phone):
    must_save = False
    if user_id and not user.user_id:
        user.user_id = user_id
        must_save = True
    if email and not user.email:
        user.email = email
        must_save = True
    if phone and not user.phone:
        user.phone = phone
        must_save = True
    if name and not user.name:
        user.name = name
        must_save = True
    if must_save:
        get_intercom_client().users.save(user)
    return user


def start_conversation(intercom_user_id, message):
    client = get_intercom_client()
    params = {
        'from': {
            'type': 'user',
            'id': intercom_user_id
        },
        'body': message
    }
    return client.messages.create(**params)


def reply(id, type, intercom_user_id, message_type, body, attachment_urls):
    client = get_intercom_client()
    return client.conversations.reply(id=id, type=type, intercom_user_id=intercom_user_id, message_type=message_type,
                                      body=body,
                                      attachment_urls=attachment_urls)
