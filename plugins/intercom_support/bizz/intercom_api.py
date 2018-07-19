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

from intercom import ResourceNotFound
from intercom.client import Client
from intercom.user import User
from mcfw.rpc import arguments, returns
from plugins.intercom_support import get_intercom_api_key


def get_intercom_client():
    return Client(personal_access_token=get_intercom_api_key())


@returns(User)
@arguments(user_id=unicode, name=unicode, email=unicode, phone=unicode)
def upsert_user(user_id, name=None, email=None, phone=None):
    # type: (unicode, unicode, unicode, unicode) -> User
    client = get_intercom_client()
    try:
        user = client.users.find(user_id=user_id)
        logging.debug('Found intercom user with user_id %s', user_id)
        return update_user_if_necessary(user, user_id, name, email, phone)
    except ResourceNotFound:
        logging.debug('No intercom user found with user_id %s, trying to find user with email %s', user_id, email)
        if email:
            try:
                # try again by searching on email
                user = client.users.find(email=email)
                logging.debug('Found user with email %s', email)
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
    if user_id and (not user.user_id or user.user_id != user_id):
        user.user_id = user_id
        must_save = True
    if email and email != user.email:
        user.email = email
        must_save = True
    if phone and not user.phone:
        user.phone = phone
        must_save = True
    if name and user.name != name:
        user.name = name
        must_save = True
    if must_save:
        logging.debug('Updating intercom user %s', user)
        get_intercom_client().users.save(user)
    return user


def send_message(from_, message, message_type='inapp', subject=None, template='plain', to=None):
    """
    Args:
        from_ (dict)
        message (unicode)
        message_type ('inapp'|'email')
        subject (unicode)
        template ('plain'|'personal')
        to (dict)
    """
    client = get_intercom_client()
    params = {
        'message_type': message_type,
        'subject': subject,
        'body': message,
        'from': from_,
        'to': to
    }
    if message_type == 'email':
        params.update({'template': template})
    return client.messages.create(**params)


def list_conversations(user_id):
    client = get_intercom_client()
    params = {
        'user_id': user_id
    }
    return client.conversations.find_all(**params)


def reply(id, type, intercom_user_id, message_type, body, attachment_urls):
    client = get_intercom_client()
    return client.conversations.reply(id=id, type=type, intercom_user_id=intercom_user_id, message_type=message_type,
                                      body=body, attachment_urls=attachment_urls)


def get_user(id=None, user_id=None, email=None):
    # type: (unicode, unicode, unicode) -> intercom.user.User
    params = {k: v for k, v, in locals().iteritems() if v}
    client = get_intercom_client()
    return client.users.find(**params)


def tag_users(tag_name, users):
    # type: (unicode, list[dict]) -> Tag
    return get_intercom_client().tags.tag(name=tag_name, users=users)
