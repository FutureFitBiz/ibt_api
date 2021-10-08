import json

from flask import jsonify, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity

from app import app, bcrypt, db, app_ids
from models import User, Company, Benchmark, Product, Impact
import utils as utils
from lib.impact import get_impact_percent_complete_stats, get_impact_question_lookup


@app.route('/investor/reports', methods=['GET'])
@jwt_required
def get_investor_reports():

    companies = []
    # completed_companies = []
    # incomplete_companies = []
    # filter_by(approved=True).\

    question_lookup = get_impact_question_lookup()

    benchmarks = Benchmark.query.\
        join(Company).\
        filter(Company.hidden != True).\
        all()

    for b in benchmarks:
        total_impacts = 0
        total_finished_impacts = 0
        be_progress = 0
        overall_progress = 0
        business_model = ''


        be_total = len([x for x in b.break_evens if x.applicable])
        be_finished = len([x for x in b.break_evens if (x.applicable and len(x.answers))])

        if be_finished:
            be_progress = (be_finished / be_total) * 100

        if b.company.business_model:
            business_model = b.company.business_model.split('(')[1].split(')')[0]

        products = []
        for p in b.products:
            impact_count = len([x for x in p.impacts if x.active])
            finished_count = 0
            for impact in p.impacts:
                if impact.active:
                    stats = get_impact_percent_complete_stats(question_lookup, impact.id)
                    if stats['percent_complete'] == 100:
                        finished_count += 1

            total_finished_impacts += finished_count
            total_impacts += impact_count

            product_progress = 0
            if finished_count:
                product_progress = (finished_count / impact_count) * 100

            products.append({
                'name': p.name,
                'type': p.type,
                'cost': p.cost,
                'revenue_type': p.revenue_type,
                'revenue': p.revenue,
                'description': p.description,
                'stage': p.stage,
                'progress': round(product_progress)
            })

        pp_progress = 0
        if total_finished_impacts:
            pp_progress = (total_finished_impacts / total_impacts) * 100

        #I think we want this to be an or not an and, because otherwise we
        #get nothign if they have not started one
        if pp_progress or be_progress:
            #I don't think we should be doing it this way, I think we should do it another way
            #I am goign to fix for now but you can remove it.....
            #overall_progress = (pp_progress + be_progress) / 2

            #this makes more sense to me
            overall_progress = ((total_finished_impacts + be_finished) / (total_impacts + be_total)) * 100

        base = {
            'id': b.company.id,
            'name': b.company.name,
            'business_model': business_model,
            'industry_type': b.company.industry_type,
            'products_count': len(b.products),
            'be_progress': "{}%".format(round(be_progress)),
            'pp_progress': "{}%".format(round(pp_progress)),
            'overall_progress': "{}%".format(round(overall_progress)),
            'description': b.company.description,
            'approved': b.approved,
            'total_revenue': b.total_revenue,
            'total_expenses': b.total_expenses,
            'products': products,
            'products_count': len(products),
            'approved_on': 0,
            'reporting_period': '',
        }


        if b.approved:
            base.update({
                'approved_on': b.approved_on,
                'reporting_period': utils.reporting_period_format(b),
            })
        companies.append(base)


    # latest = sorted(companies, key=lambda x: x['approved_on'], reverse=True)[:3]
    companies = sorted(companies, key=lambda x: x['name'])

    return jsonify({
        'total_impacts': total_impacts,
        # 'total': len(res),
        'companies': companies,
        # 'completed_companies': completed_companies,
        # 'incomplete_companies': incomplete_companies,
        'latest': []
        # 'latest': latest
    })



@app.route('/investor/stats', methods=['GET'])
@jwt_required
def get_investor_stats():
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
