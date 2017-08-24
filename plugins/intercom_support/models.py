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

from plugins.intercom_support import plugin_consts


class RogerthatConversation(ndb.Model):
    intercom_support_message_id = ndb.StringProperty(indexed=False)
    intercom_support_chat_id = ndb.StringProperty(indexed=False)

    @classmethod
    def create_key(cls, user_id, chat_id):
        return ndb.Key(cls, chat_id, parent=User.create_key(user_id), namespace=plugin_consts.NAMESPACE)


class IntercomConversation(ndb.Model):
    rogerthat_chat_id = ndb.StringProperty(indexed=False)

    @classmethod
    def create_key(cls, user_id, chat_id):
        return ndb.Key(cls, chat_id, parent=User.create_key(user_id), namespace=plugin_consts.NAMESPACE)


class User(ndb.Model):
    @classmethod
    def create_key(cls, user_id):
        return ndb.Key(cls, user_id, namespace=plugin_consts.NAMESPACE)
