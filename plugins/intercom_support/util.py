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
from google.appengine.api import users

from framework.utils import azzert
from mcfw.rpc import returns, arguments
from plugins.rogerthat_api.to import UserDetailsTO

APP_ID_ROGERTHAT = u'rogerthat'


@returns(unicode)
@arguments(user=(users.User, UserDetailsTO))
def get_username(user):
    # Assuming oauth registration here
    if isinstance(user, users.User):
        email = get_human_user_from_app_user(user).email()
    else:
        email = user.email
    return email.rsplit('@', 1)[0]


@returns(users.User)
@arguments(app_user=users.User)
def get_human_user_from_app_user(app_user):
    return get_app_user_tuple(app_user)[0]


@returns(unicode)
@arguments(app_user=users.User)
def get_app_id_from_app_user(app_user):
    return get_app_user_tuple(app_user)[1]


@returns(tuple)
@arguments(app_user=users.User)
def get_app_user_tuple(app_user):
    # type: (users.User) -> tuple
    return get_app_user_tuple_by_email(app_user.email())


@returns(tuple)
@arguments(app_user_email=unicode)
def get_app_user_tuple_by_email(app_user_email):
    azzert('/' not in app_user_email, "app_user_email should not contain /")
    if ':' in app_user_email:
        human_user_email, app_id = app_user_email.split(':')
    else:
        human_user_email, app_id = app_user_email, APP_ID_ROGERTHAT
    return users.User(human_user_email), app_id


@returns(users.User)
@arguments(human_user=users.User, app_id=unicode)
def create_app_user(human_user, app_id=None):
    return create_app_user_by_email(human_user.email().decode('utf-8'), app_id)


@returns(users.User)
@arguments(human_user_email=unicode, app_id=unicode)
def create_app_user_by_email(human_user_email, app_id):
    azzert('/' not in human_user_email, "human_user_email should not contain /")
    azzert(':' not in human_user_email, "human_user_email should not contain :")
    azzert(app_id, "app_id should not be empty")
    if app_id != APP_ID_ROGERTHAT:
        return users.User(u"%s:%s" % (human_user_email, app_id))
    return users.User(human_user_email)
