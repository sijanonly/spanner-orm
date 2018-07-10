#!flask/bin/python
import sys

sys.path.insert(0, '..')

import logging
from time import time
from datetime import date
from models import User, Role, Organization
from flask import Flask, jsonify, g, request
from spannerorm import Connection, Criteria, ModelJSONEncoder

app = Flask(__name__)
app.json_encoder = ModelJSONEncoder
logging.basicConfig(level=logging.DEBUG)

service_account_json = '/home/leapfrog/personal-data/python-work/opensource/spanner-orm/service_account.json'
Connection.config('develop', 'auth', service_account_json)


@app.before_request
def before_request():
    logging.debug('Request [{request_method}] : {request_url}'
                  .format(request_method=request.method, request_url=request.base_url))
    g.start_time = time()


@app.after_request
def after_request(response):
    execution_time = time() - g.start_time
    logging.debug('Request completion time: {execution_time}'.format(execution_time=execution_time))
    return response


@app.route('/')
def root():
    return 'example api'

@app.route('/user/meta')
def user_meta_data():
    return jsonify(User.get_meta_data())

@app.route('/user/one')
def one_user():
    criteria = Criteria()
    criteria.condition([(User.role_id, '=', '1'), (User.organization_id, '=', '4707145032222247178')])
    criteria.add_condition((User.is_deleted, '=', False))
    user = User.find(criteria)
    return jsonify(user)

@app.route('/user/by_pk')
def user_by_pk():
    criteria = Criteria()
    criteria.add_condition((User.is_deleted, '=', False))
    user = User.find_by_pk('-300113230644022007', criteria)
    return jsonify(user)

@app.route('/user/find_all')
def find_all_users():
    criteria = Criteria()
    criteria.condition([(User.email, 'LIKE', '%@lftechnology.com')])
    criteria.add_condition((User.role_id, 'IN', ['1', '2']))
    criteria.add_condition((User.organization_id, 'NOT IN', ['4707145032222247178']))
    criteria.set_order_by(User.email, 'ASC')
    criteria.limit = 2

    users = User.find_all(criteria)
    return jsonify(users)

@app.route('/user/find_all_with')
def find_all_user_with():
    criteria = Criteria()
    criteria.join_with(User.role)
    criteria.join_with(User.organization)
    criteria.condition([(User.email, 'LIKE', '%@lftechnology.com')])
    criteria.set_order_by(User.email, 'ASC')
    criteria.limit = 2

    users = User.find_all(criteria)
    for user in users:
        print(user.role)

    return jsonify(users)

@app.route('/role/users')
def role_one_to_many_users():
    criteria = Criteria()
    criteria.join_with(Role.users)
    criteria.add_condition((User.email, '=', 'mjsanish+admin@gmail.com'))
    criteria.set_order_by(User.email, order='DESC')
    role = Role.find(criteria)
    return jsonify(role)

@app.route('/user/insert_block')
def insert_block():
    data_list = [{
        'email': 'mjsanish+1@gmail.com',
        'name': 'sanish1',
        "is_deleted": False,
        'organization_id' : '4707145032222247178',
        'role_id': '1',
        'created_by': '-1202895510759970011',
    }, {
        'email': 'mjsanish+2@gmail.com',
        'name': 'sanish2',
        "is_deleted": False,
        'organization_id' : '4707145032222247178',
        'role_id': '1',
        'created_by': '-1202895510759970011',
    }]

    users = User.insert_block(data_list)
    return jsonify(users)

@app.route('/user/update_block')
def update_block():
    data_list = [{
        'id': '271fc766-6de7-44c7-bd1c-b04954cd401f',
        'email': 'mjsanish+100@gmail.com',
        'name': 'sanish100'
    }, {
        'id': '20b2e97f-4c77-460b-9324-bb7530d6b8f7',
        'role_id': '2'
    }]

    users = User.update_block(data_list)
    return jsonify(users)

@app.route('/user/save')
def save_user():
    user = User()
    user.id = User._meta().generate_pk()
    user.name = 'some one'
    user.email = 'someone@gmail.com'
    user.organization_id = '4707145032222247178'
    user.role_id = '1'
    user.created_at = time()
    user.created_by = '-1202895510759970011'

    user = User.save(user)
    return jsonify(user)

@app.route('/user/update')
def update_user():
    user = User.find_by_pk('d3fefb2a-ef30-4c39-a560-81b459f5024e')
    user.name = 'some one'
    user.email = 'someone@gmail.com'
    user.organization_id = '4707145032222247178'
    user.role_id = '1'

    user = User.save(user)
    return jsonify(user)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8282, debug=True)