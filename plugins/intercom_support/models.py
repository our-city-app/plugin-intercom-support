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

from google.appengine.ext import ndb

from framework.models.common import NdbModel
from plugins.intercom_support.plugin_consts import NAMESPACE


class RogerthatConversation(NdbModel):
    NAMESPACE = NAMESPACE

    intercom_support_message_id = ndb.StringProperty(indexed=False)
    intercom_support_chat_id = ndb.StringProperty(indexed=False)

    @property
    def rogerthat_chat_id(self):
        return self.key.id().decode('utf-8')

    @classmethod
    def create_key(cls, user_id, chat_id):
        return ndb.Key(cls, chat_id, parent=User.create_key(user_id), namespace=NAMESPACE)

    @classmethod
    def get_by_user(cls, user_id):
        return cls.query(ancestor=User.create_key(user_id)).get()


class IntercomConversation(NdbModel):
    NAMESPACE = NAMESPACE

    rogerthat_chat_id = ndb.StringProperty(indexed=False)

    @classmethod
    def create_key(cls, user_id, chat_id):
        return ndb.Key(cls, chat_id, parent=User.create_key(user_id), namespace=NAMESPACE)


class User(NdbModel):
    NAMESPACE = NAMESPACE

    @classmethod
    def create_key(cls, user_id):
        return ndb.Key(cls, user_id, namespace=NAMESPACE)
