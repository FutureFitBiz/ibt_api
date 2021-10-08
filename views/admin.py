import json

from flask import jsonify, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity

from app import app, bcrypt, db
from models import User, Company, Benchmark, Product, Impact
import utils as utils
from lib.email import send_reset_password_email, send_welcome_email


@app.route('/admin/stats', methods=['GET'])
@jwt_required
def get_admin_stats():
    total_users = User.query.count()
    admin_users = User.query.filter_by(admin=True).count()
    companies = Company.query.count()
    products = Product.query.count()
    impacts = Impact.query.count()
    users = total_users - admin_users

    data = {
        'total_users': total_users,
        'admin_users': admin_users,
        'users': users,
        'companies': companies,
        'products': products,
        'impacts': impacts,
    }

    return jsonify(data)


@app.route('/admin/user', methods=['GET'])
@jwt_required
def get_admin_users():
    users = User.query.all()
    data = []
    for user in users:
        data.append({
            'id': user.id,
            'email': user.email,
            'first': user.first,
            'last': user.last,
            'admin': user.admin,
            'investor': user.investor,
            'company_id': user.company_id,
            'company': user.company.name if user.company else 'None',
        })

    return jsonify({
        'status': 'success',
        'data': data
    })

    return jsonify(response)


@app.route('/admin/user/<int:id>', methods=['GET'])
@jwt_required
def get_user(id):
    user = User.query.get(id)
    data = {
        'id': user.id,
        'email': user.email,
        'admin': user.admin,
        'investor': user.investor,
        'company_id': user.company_id,
        'first': user.first,
        'last': user.last,
        'password': None
    }
    return jsonify(data)


@app.route('/admin/user', methods=['POST'])
@jwt_required
def save_user():
    """
    Update user or create new
    """
    response = {'status': 'success', 'message': 'user saved'}
    data = request.json.get('data')

    user = None
    if data.get('id'):
        user = User.query.get(data['id'])
    else:
        user = User()
        user.password = utils.new_bcrypt_password()

    # required
    if data['email']:
        found = User.query.filter_by(email=data['email']).one_or_none()
        if data.get('id') is None or user.email != data['email']:
            if found:
                response = {'status': 'error', 'message': 'email already in use'}


    if response['status'] == 'success':
        user.email = data['email']
        user.first = data['first']
        user.last = data.get('last')

        # optional
        user.admin = data.get('admin')
        user.investor = data.get('investor')
        company_id = data.get('company_id')

        if company_id:
            benchmark = Benchmark.query.filter_by(company_id=company_id).first()
            user.company_id = company_id
            user.benchmark_id = benchmark.id

        db.session.add(user)
        db.session.commit()

    return jsonify(response)


@app.route('/admin/user/delete/<int:id>', methods=['GET'])
@jwt_required
def delete_user(id):
    user = User.query.get(id)
    if user:
        db.session.delete(user)
        db.session.commit()

    return jsonify({'status': 'success'})


@app.route('/admin/company', methods=['GET'])
@jwt_required
def get_companies():
    companies = Company.query.all()
    data = []
    for c in companies:
        # they only ever have one for now..
        b = c.benchmarks[0]
        pp_total = len(b.products)
        pp_finished = 0

        for product in b.products:
            impacts = Impact.query.filter_by(product_id=product.id, active=1).all()
            total = len(impacts)
            count = 0
            for imp in impacts:
                if imp.answers:
                    count += 1
            if total == count:
                pp_finished += 1

        pp_percent = 0
        if pp_total and pp_finished:
            pp_percent = round((pp_finished / pp_total) * 100)

        be_total = len(b.break_evens)
        be_finished = len([be for be in b.break_evens if be.answers])
        be_percent = 0
        if be_finished and be_total:
            be_percent = round((be_finished / be_total) * 100)

        data.append({
            'id': c.id,
            'name': c.name,
            'intro_complete': c.intro_complete,
            'description': c.description,
            'industry_type': c.industry_type,
            'user_count': len(c.users),
            'benchmark_count': len(c.benchmarks),
            'product_count': len(b.products),
            'business_model': c.business_model,
            'year': b.year,
            'month_start': b.month_start,
            'month_end': b.month_end,
            'hidden': c.hidden,
            'pp_percent': pp_percent,
            'pp_total': pp_total,
            'pp_finished': pp_finished,
            'be_percent': be_percent,
            'be_total': be_total,
            'be_finished': be_finished,

        })

    return jsonify({
        'status': 'success',
        'data': data
    })


@app.route('/admin/company', methods=['POST'])
@jwt_required
def create_company():
    data = request.json.get('data')
    company = Company.query.filter_by(name=data['name']).first()

    if data.get('id'):
        company = Company.query.get(data['id'])
    else:
        company = Company()
        db.session.add(company)
        message = 'company added'

        benchmark = Benchmark()
        benchmark.year = data.get('year')
        benchmark.month_start = data.get('month_start')
        benchmark.month_end = data.get('month_end')

        db.session.add(benchmark)
        benchmark.company = company

    # required
    company.name = data['name']
    # optional
    company.intro_complete = True
    company.hidden = data.get('hidden')
    company.industry_type = data.get('industry_type')
    company.description = data.get('description')
    company.business_model = data.get('business_model')

    db.session.commit()

    return jsonify({'status': 'success', 'message': 'company saved'})


@app.route('/admin/company/delete/<int:id>', methods=['GET'])
@jwt_required
def delete_company(id):
    company = Company.query.get(id)
    if company:
        db.session.delete(company)
        db.session.commit()

    return jsonify({'status': 'success'})


# @jwt_required
@app.route('/admin/email/<type>/<int:user_id>', methods=['GET'])
def send_email(type, user_id):
    user = User.query.get(user_id)
    res = {'status': 'error', 'message': 'error sending email'}
    pw = utils.random_uuid_code()
    bcrypt_pw = utils.new_bcrypt_password(pw)
    print(user)

    if type == 'welcome':
        send_welcome_email(user.email, pw)
        user.password = bcrypt_pw
        db.session.commit()
        res = {'status': 'success', 'message': 'welcome email sent'}
    if type == 'reset':
        send_reset_password_email(user.email, pw)
        user.password = bcrypt_pw
        db.session.commit()
        res = {'status': 'success', 'message': 'reset email sent'}

    return jsonify(res)
