import io
import re
import csv
import time
import json
import random
from datetime import datetime

from flask import jsonify, request, render_template, session, make_response, Response, send_file
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity

from app import app, bcrypt, settings, db
from lib.impact import surveys, get_impact_description
from models import User, Company, Product, Benchmark, ProductFacet,\
    ProductProperty, ProductPropertyAnswer, Impact, ImpactSdg, ImpactAnswer,\
    BreakEven, BreakEvenAnswer
from lib.email import send_reset_password_email

import utils as utils

if settings.DEBUG:
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context


stakeholder_name_question = 'A-1'
intensity_duration = 'A-17'
intensity_significance = 'A-18'
intensity_proportion = 'A-21'
scale_question = 'A-15'
scale_unit = 'people'
depth_value_question = 'A-9'
depth_unit_question = 'A-10'

individual_stakeholder_options = [
    'A-1.1',  # Customers (Individuals)
    'A-1.3',  #  Indirect Consumers/Community Members
    'A-1.4'  # Employees
]
# hardcoded units for investment chart
scale_depth_units = {
    'A-1.1': 'Customers',
    'A-1.3': 'Indirect Consumers',
    'A-1.4': 'Employees',
}

default_menu_items = [
    {
        'title': 'Home',
        'path': 'home',
    },
    {
        'title': 'Positive Impacts',
        'path': 'positive-impacts',
        'items': [{
            'title': 'Manage Activities',
            'path': 'manage'
        },
        ]
    },
    {
        'title': 'ESG Risks',
        'path': 'esg-risks',
    },
    {
        'title': 'Reports',
        'path': 'reports',
        'items': [
            {
                'title': 'Positive Impacts',
                'path': 'positive-impact'
            },
            {
                'title': 'ESG Risks',
                'path': 'esg-risk'
            },
            {
                'title': 'Data',
                'path': 'data'
            },
            {
                'title': 'PDF Report',
                'path': 'download'
            },
        ]
    }
]

ALLOWED_IMAGE_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


@app.route('/test/email/<type>')
def test_email(type):
    res = 'unknown'
    if type == 'welcome':
        res = render_template('emails/welcome.html', password='testpassword', email='test@test.com')
    if type == 'reset':
        res = render_template('emails/reset_password.html', password='testpassword')

    return res


@app.route('/')
def home():
    return render_template('home.html')


def get_all_answer_codes(options):
    codes = []
    for q in options:
        value = q.get('value')
        if value:
            codes.append(value)
        o = q.get('options')
        if o:
            codes += get_all_answer_codes(o)
    return codes


@app.route('/reset/password', methods=['POST'])
def reset_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    data = {'status': 'success'}

    if user:
        try:
            new_password = utils.random_uuid_code()
            send_reset_password_email(email, new_password)
            user.password = utils.new_bcrypt_password(new_password)
            db.session.commit()
            data['message'] = 'email sent'
        except Exception as e:
            time.sleep(2)
            data = {'status': 'error', 'message': 'error sending email'}
            print(e)
    else:
        time.sleep(2)
        data = {'status': 'error', 'message': 'email not found'}

    return jsonify(data)


@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')
    app = request.json.get('app')
    if app:
        app = app.lower()

    if not email or not password:
        return jsonify({"message": "Missing username/password"})

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"message": "Invalid username/password"})

    if (app == 'admin' and not user.admin) or (app == 'investor' and not user.investor):
        return jsonify({"message": "Incorrect permissions"})

    access_token = create_access_token(identity=email)

    res = {
        'access_token': access_token,
        'intro_complete': user.company.intro_complete if user.company else False,
        'benchmark_id': user.benchmark_id,
        'email': user.email,
        'company_name': user.company.name if user.company else '',
        'first': user.first,
        'last': user.last,
        'welcome': user.welcome,
    }
    if app != 'admin':
        res['menu_items'] = default_menu_items

    return jsonify(res)


@app.route('/user/company', methods=['GET'])
@jwt_required
def company_info():
    response = {'status': 'error', 'message': 'no company'}
    user = User.query.filter_by(email=get_jwt_identity()).first()
    company = user.company
    b = user.benchmark

    if company:
        response = {
            'status': 'success',
            'user_email': user.email,
            'user_first': user.first,
            'company': {
                'name': company.name,
                'description': company.description,
                'industry_type': company.industry_type,
                'business_model': company.business_model,
                'total_revenue': b.total_revenue,
                'id': company.id,
                'reporting_period': utils.reporting_period_format(b),
            }
        }
    return jsonify(response)


@app.route('/user/welcome_complete', methods=['GET'])
@jwt_required
def welcome_complete():
    user = User.query.filter_by(email=get_jwt_identity()).first()
    user.welcome = True
    db.session.commit()
    return jsonify({'status': 'success'})


@app.route('/benchmark/status', methods=['GET'])
@jwt_required
def get_benchmark_status():
    user = User.query.filter_by(email=get_jwt_identity()).first()

    return jsonify({
        'status': 'success',
        'approved': user.benchmark.approved,
    })


@app.route('/benchmark/status', methods=['POST'])
@jwt_required
def update_benchmark_status():
    user = User.query.filter_by(email=get_jwt_identity()).first()
    approved = request.json.get('approved', False)
    user.benchmark.approved = approved
    stamp = time.time()

    user.benchmark.approved_on = stamp
    db.session.commit()

    return jsonify({
        'status': 'success',
    })


@app.route('/user/profile', methods=['GET'])
@jwt_required
def get_profile():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()

    return jsonify({
        'email': user.email,
        'first': user.first,
        'last': user.last,
    })


@app.route('/user/profile', methods=['POST'])
@jwt_required
def update_profile():
    email = get_jwt_identity()
    data = request.json.get('data')
    total_revenue = data.get('total_revenue')

    user = User.query.filter_by(email=email).first()
    user.email = data['email']
    user.first = data.get('first')
    user.last = data.get('last')

    pw = data.get('password')
    new_pw = data.get('new_password')
    if pw and new_pw:
        if bcrypt.check_password_hash(user.password, pw):
            user.password = utils.new_bcrypt_password(new_pw)
        else:
            return jsonify({'status': 'error', 'message': ['Wrong password']})

    db.session.commit()

    return jsonify({'status': 'success', 'message': 'profile updated'})


@app.route('/company/profile', methods=['GET'])
@jwt_required
def get_benchmark():
    email = get_jwt_identity()
    user = User.query.filter_by(email=email).first()
    warnings = []
    if user.benchmark.total_revenue == 0:
        warnings.append('Total revenue is 0')
    if user.benchmark.total_expenses == 0:
        warnings.append('Total expenses is 0')
    if user.company.industry_type == 0:
        warnings.append('Missing: Industry')

    return jsonify({
        'warnings': warnings,
        'name': user.company.name,
        'industry_type': user.company.industry_type,
        'business_model': user.company.business_model,
        'description': user.company.description,
        #
        'month_start': user.benchmark.month_start,
        'month_end': user.benchmark.month_end,
        'year': user.benchmark.year,
        'total_revenue': user.benchmark.total_revenue,
        'total_expenses': user.benchmark.total_expenses,
        'reporting_period': utils.reporting_period_format(user.benchmark)
    })


@app.route('/company/profile', methods=['POST'])
@jwt_required
def update_benchmark():
    data = request.json.get('data')
    total_revenue = data.get('total_revenue')
    user = User.query.filter_by(email=get_jwt_identity()).first()

    company = user.company
    company.name = data['name']
    company.industry_type = data.get('industry_type')
    company.business_model = data['business_model']
    company.description = data.get('description')

    # tbd, how we do benchamrks will change this
    benchmark = user.benchmark
    benchmark.year = data['year']
    benchmark.month_end = data.get('month_end')
    benchmark.month_start = data.get('month_start')
    benchmark.total_revenue = data.get('total_revenue', 0)
    benchmark.total_expenses = data.get('total_expenses', 0)

    db.session.commit()

    return jsonify({'status': 'success', 'message': 'saved'})


@app.route('/company/db/img/<company_id>')
def serve_db_company_image(company_id):
    """
    stream a company db blob image to the browser
    """
    company = Company.query.get(company_id)

    if not company.logo:
        return

    file_stream = s3_manager.get_file_stream(url)
    file_stream.seek(0)
    extension = image_file.rsplit('.', 1)[1].lower()

    return send_file(company.logo, mimetype='image/%s' % company.logo_file_extension)


@app.route('/company_intro', methods=['POST'])
@jwt_required
def update_company_info():
    # they (should) only do once
    email = get_jwt_identity()
    response = {'status': 'success'}

    data = request.json.get('data')

    company = Company()
    company.name = data['company_name']
    company.description = data.get('company_description')
    company.industry_type = data['industry_type']
    company.business_model = data['business_model']

    # company.reason_of_use = data.get('reason_of_use')
    company.intro_complete = True
    db.session.add(company)

    benchmark = Benchmark()
    benchmark.year = data['year']
    benchmark.month_start = data['month_start']
    benchmark.month_end = data['month_end']
    benchmark.total_revenue = data.get('total_revenue')
    benchmark.total_expenses = data.get('total_expenses')
    benchmark.company = company
    db.session.add(benchmark)

    # add company to user, there will be no company id before commiting
    user = User.query.filter_by(email=email).first()
    user.company = company
    user.benchmark = benchmark

    db.session.commit()

    return jsonify(response)


@app.route('/company/logo', methods=['POST'])
@jwt_required
def update_company_logo():
    # they (should) only do once
    response = {'status': 'success'}

    # look for company - if not there add company to user, there will be no company id before commiting
    user = User.query.filter_by(email=email).first()
    user.company = company
    user.benchmark = benchmark

    data = request.json.get('data')

    company = Company()
    company.name = data['company_name']
    company.description = data.get('company_description')
    company.industry_type = data['industry_type']
    company.business_model = data['business_model']

    # company.reason_of_use = data.get('reason_of_use')
    company.intro_complete = True
    db.session.add(company)

    benchmark = Benchmark()
    benchmark.year = data['year']
    benchmark.month_start = data['month_start']
    benchmark.month_end = data['month_end']
    benchmark.total_revenue = data.get('total_revenue')
    benchmark.total_expenses = data.get('total_expenses')
    benchmark.company = company
    db.session.add(benchmark)

    db.session.commit()

    return jsonify(response)


@app.route('/survey/<name>', methods=['GET'])
@jwt_required
def get_action_survey(name):
    lookup = {
        'pp_action': surveys.pp_action,
        'facets': surveys.facets,
        'properties': surveys.properties,
        'add_edit_product': surveys.add_edit_product,
    }
    return jsonify(lookup.get(name))

def get_be_percent_complete_stats(question_lookup, be):
    #run through the answers and see if we have answerd all that is visible - based on the answers
    answers = {}
    stats = {}
    visible_questions = 0
    answered_questions = 0
    percent_complete = 0
    be_questions = question_lookup[be.code]

    current_answers = BreakEvenAnswer.query.filter_by(break_even_id=be.id).all()

    for current_answer in current_answers:
        answers[current_answer.code] = current_answer.data

    for number in be_questions:
        question = be_questions[number]
        stats[number] = {'answered': False,
                         'visible': True}

        for logic in question['logic']:
            #only care about logic lists that actually have something
            if len(logic) > 0:
                intersection = [x for x in answers.values() if x in logic]
                if len(intersection) == 0:
                    stats[number]['visible'] = False

        if number in answers:
            stats[number]['answered'] = True

    for key in stats:
        if stats[key]['visible']:
            visible_questions += 1
            if stats[key]['answered']:
                answered_questions += 1

    if visible_questions > 0 and answered_questions > 0:
        percent_complete = round((answered_questions / visible_questions) * 100)

    return {'visible_questions': visible_questions,
            'percent_complete': percent_complete,
            'answered_questions': answered_questions}


def get_be_question_lookup():
    #get the questions so we can see if all that is needed
    question_lookup = {}

    for code in surveys.be:
        questions = surveys.be[code]['questions']
        question_lookup[code] = {}
        for question in questions:
            if 'number' in question:
                question_lookup[code][question['value']] = question

    return question_lookup


@app.route('/survey/be/<code>', methods=['GET'])
@jwt_required
def get_be_survey(code):
    return jsonify(surveys.be[code])



@app.route('/be', methods=['GET'])
@jwt_required
def get_all_break_evens():
    break_evens = []
    categories = []
    # user = User.query.filter_by(email='tester@futurefitbusiness.org').first()
    user = User.query.filter_by(email=get_jwt_identity()).first()
    benchmark_id = user.benchmark.id
    question_lookup = get_be_question_lookup()

    break_evens = BreakEven.query.filter_by(benchmark_id=benchmark_id).all()

    if not break_evens:
        for code in surveys.be_tags:
            be = BreakEven()
            be.benchmark_id = benchmark_id
            be.code = code
            db.session.add(be)
        db.session.commit()

        break_evens = BreakEven.query.filter_by(benchmark_id=benchmark_id).all()

    lookup = {}

    for be in break_evens:
        lookup[be.code] = be

    menu_items = surveys.be_text_lookup['menu_items']

    for category in menu_items:
        for item in category['items']:
            be = lookup[item['code']]
            scores = surveys.be[be.code]['scores']

            #do we want to start saving this?
            stats = get_be_percent_complete_stats(question_lookup, be)
            item.update({
                'id': be.id,
                'percent_complete': stats['percent_complete'],
                'awareness_score': be.awareness_score,
                'awareness_unit': scores['awareness']['unit'],
                'progress_score': be.progress_score,
                'progress_unit': scores['progress']['unit'],
                'complete': len(be.answers) > 0,
                'applicable': be.applicable,
            })

    for category in menu_items:
        total = len(category['items'])
        percent = 0
        total_complete = 0
        for item in category['items']:
            percent += item['percent_complete']
            if item['percent_complete'] == 100:
                total_complete += 1

        category['percent_complete'] = round(percent / total)
        category['total'] = total
        category['total_complete'] = total_complete

    return jsonify(menu_items)


def get_be_json(be):
    info = surveys.be_text_lookup['break_evens'][be.code]
    be_info = surveys.be[be.code]
    applicable_text = 'incomplete'
    if be.applicable is not None:
        applicable_text = 'yes' if be.applicable else 'no'

    return {
        'id': be.id,
        'code': be.code,
        'title': info['short_name'],
        'middle_name': info['middle_name'],
        'long_name': info['long_name'],
        'category': info['category'],
        'category_path': info['category_path'],
        'path': info['path'],
        'progress_score': be.progress_score,
        'progress_unit': be_info['scores']['progress']['unit'],
        'awareness_score': be.awareness_score,
        'awareness_unit': be_info['scores']['progress']['unit'],
        'complete': len(be.answers) > 0,
        'applicable': be.applicable,
        'applicable_text': applicable_text,

    }


@app.route('/be/<int:id>', methods=['GET'])
@jwt_required
def get_be_answers(id):
    res = {}
    answers = BreakEvenAnswer.query.filter_by(break_even_id=id).all()

    for answer in answers:
        res[answer.code] = answer.data

    return jsonify({'answers': res})


@app.route('/be/categories', methods=['GET'])
@jwt_required
def get_be_categories(id):
    categories = []
    surveys.be_categories
    return jsonify({'title': res})


@app.route('/be/next', methods=['GET'])
@jwt_required
def get_next_break_even():
    next_be = {}

    user = User.query.filter_by(email=get_jwt_identity()).first()
    benchmark_id = user.benchmark.id
    break_evens = BreakEven.query.filter_by(benchmark_id=benchmark_id).all()

    ordering = surveys.be_text_lookup['be_order']
    break_evens = sorted(break_evens, key=lambda x: ordering[x.code])

    for be in break_evens:
        if len(be.answers) == 0:
            next_be = get_be_json(be)
            break

    if not next_be:
        next_be = {'code': 'finished', }
    return jsonify(next_be)


@app.route('/be/<int:id>', methods=['POST'])
@jwt_required
def save_be_answers(id):
    data = request.json.get('data')
    be = BreakEven.query.get(id)
    current_answers = BreakEvenAnswer.query.filter_by(break_even_id=id).all()

    for answer in current_answers:
        db.session.delete(answer)

    for key in data:
        answer = BreakEvenAnswer()
        answer.break_even_id = id
        answer.code = key
        answer.data = data[key]
        db.session.add(answer)

    applicable = None
    for value in data.values():
        # applicable == clicking on the first question
        if '-1.' in value:
            option = value.split('-1.')[1]
            applicable = option == '1'

    scores = surveys.be[be.code]['scores']
    progress_score = calculate_be_score(scores['progress']['score'], data)
    awareness_score = calculate_be_score(scores['awareness']['score'], data)

    be.progress_score = progress_score
    be.awareness_score = awareness_score
    be.applicable = applicable
    db.session.commit()

    return jsonify({
        'status': 'success',
        'awareness_score': awareness_score,
        'awareness_unit': scores['awareness']['unit'],
        'progress_score': progress_score,
        'progress_unit': scores['progress']['unit'],
        'applicable': applicable,
    })


def calculate_be_score(formula, data):
    questions = extract_questions(formula)
    updated_formula = formula

    for q in questions:
        value = 0
        answer = data.get(q)
        if answer:
            value = float(find_value(answer))

        updated_formula = updated_formula.replace(q.strip(), str(value))

    try:
        inner_parts = re.findall("\(([^(\)]*)\)", updated_formula)
        for part in inner_parts:
            res = 0
            try:

                res = float(eval(part))
            except ZeroDivisionError:
                pass

            updated_formula = updated_formula.replace(part, str(res))

        score = round(eval(updated_formula))
    except ZeroDivisionError:
        score = 0

    return score


def extract_questions(formula):
    # ie forumla = '( BE21-4 + BE21-5 + BE21-6 + BE21-7  ) / 4 * 100'
    endings = ['(', ')', '+', '*', ' ']
    questions = []
    code = ''
    dash_count = 0
    adding = False
    for char in formula:
        if char == '-':
            dash_count += 1
        if char in endings or dash_count > 1:
            # there's only one dash ever in a question, so it must be a minus instead
            adding = False
            if code:
                questions.append(code)
                code = ''
                dash_count = 0
        if char == 'B':
            adding = True
        if adding:
            code += char

    return questions


def find_value(answer):
    val = answer

    if isinstance(answer, str):
        if 'BE' in answer:
            tokens = answer.split('-')
            be_code = tokens[0]
            q_number = tokens[1].split('.')[0]
            q_option = tokens[1].split('.')[1]
            questions = surveys.be[be_code]['questions']

            for q in questions:
                if q.get('number') == q_number:
                    options = q.get('options')

                    if options:
                        for o in options:
                            if o['value'] == answer:
                                option_value = o.get('option_value')

                                if not option_value:
                                    # if it doesn't have a specific value
                                    option_value = int(q_option) - 1

                                val = option_value

    return val


def split_additional_pages(items, first_page_count, page_count):
    """
    for when items get out of hand in the pdf
    """
    res = []

    if len(items) <= first_page_count:
        # just return the one page
        res = [items]
    elif len(items) <= first_page_count + page_count:
        res = [items[0:first_page_count], items[first_page_count:]]
    else:
        # split into additional ones
        additional_pages = items[first_page_count:]
        res = [items[0:first_page_count]]

        while len(additional_pages) > page_count:
            chunk = additional_pages[0:page_count]
            additional_pages = additional_pages[page_count:]
            res.append(chunk)
    return res


def _convert_intensity_answer(answers, question):
    # "x.x.1" becomes 0
    answer = answers.get(question, 0)
    if answer:
        answer = int(answer[-1]) - 1
    return answer


def _get_intensity(answers):
    duration = _convert_intensity_answer(answers, intensity_duration)
    significance = _convert_intensity_answer(answers, intensity_significance)
    proportion = _convert_intensity_answer(answers, intensity_proportion)

    score = 1 + duration + significance + proportion

    return {
        'score': score,
        'duration': duration,
        'significance': significance,
        'proportion': proportion,
    }


@app.route('/report/pp', methods=['GET'])
@jwt_required
def get_positive_impact_report_data():
    for_pdf = request.args.get('forPDF', False) == 'true'
    benchmark = get_app_benchmark(request)
    products = pre_load_products_and_impacts(benchmark)

    return jsonify({
        'stacked': get_chart_pp_stacked(products, for_pdf),
        'chart_2': get_chart_pp_chart_2(products, for_pdf),
        'investment': get_chart_investment(products, for_pdf),
        'data_table': get_chart_pp_data_table(products, for_pdf),
    })


@app.route('/report/be', methods=['GET'])
@jwt_required
def get_break_even_report_data():
    for_pdf = request.args.get('forPDF', False) == 'true'
    benchmark = get_app_benchmark(request)
    break_evens = benchmark.break_evens

    return jsonify({
        'data_table': be_data_table(break_evens),
        'best_and_worst': get_chart_be_best_and_worst(break_evens),
        'overview': get_chart_be_overview(break_evens, for_pdf)
    })


def be_data_table(break_evens):
    return [get_be_json(be) for be in break_evens]


def get_app_benchmark(request):
    app = request.args.get('app')
    company_id = request.args.get('company_id')
    if app == 'INVESTOR':
        # there's only one for now..
        benchmark = Benchmark.query.filter_by(company_id=int(company_id)).first()
    else:
        # user = User.query.filter_by(email='tester@futurefitbusiness.org').first()
        user = User.query.filter_by(email=get_jwt_identity()).first()
        benchmark = user.benchmark

    return benchmark


@app.route('/report/download/csv', methods=['GET'])
@jwt_required
def get_report_csv():
    benchmark = get_app_benchmark(request)
    break_evens = benchmark.break_evens
    products = pre_load_products_and_impacts(benchmark)
    break_evens = be_data_table(break_evens)
    pp = get_chart_pp_data_table(products)

    filename = "{} {}".format(benchmark.company.name, utils.reporting_period_format(benchmark))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Impact Benchmark Repot Data'])
    writer.writerow([filename])

    # PP
    writer.writerow(['Positive Impacts'])
    pp_headers = [
        'Activity',
        'Impact',
        'Applicable',
        'FF Positive Pursuit',
        'SDGs',
        'Stakeholder',
        'Measurement Type',
        'Duration',
        'Significance',
        'Proportion',
        'Intensity',
        'Scale',
        'Depth',
        'Depth Unit',
    ]
    writer.writerow(pp_headers)

    for item in pp:
        row = [
            item['name'],
            item['impact'],
            item['applicable'],
            item['pp_action'],
            item['sdgs'],
            item['stakeholder'],
            item['measurement_type'],
            item['intensity_duration'],
            item['intensity_significance'],
            item['intensity_proportion'],
            item['intensity'],
            item['scale'],
            item['depth_value'],
            item['depth_unit'],
        ]
        writer.writerow(row)

    # BE
    writer.writerow(['ESG Risks'])
    be_headers = [
        'FF Goal',
        'Business Area',
        'Title',
        'Applicable',
        'Data awareness',
        'Progress Indicator',
        'Progress Unit'
    ]
    writer.writerow(be_headers)
    for be in break_evens:
        row = [
            be['code'],
            be['category'],
            be['long_name'],
            be['applicable_text'],
            be['awareness_score'] if be['applicable'] else '',
            be['progress_score'] if be['applicable'] else '',
            be['progress_unit'] if be['applicable'] else '',
        ]

        writer.writerow(row)

    output.seek(0)
    res = make_response(output.getvalue())
    res.headers["Content-Disposition"] = "attachment; filename={}.csv".format(filename)
    res.headers["Content-type"] = "text/csv"
    return res


def pre_load_products_and_impacts(benchmark):
    products = []

    for product in benchmark.products:
        relative_cost = 'n/a'
        if product.cost and benchmark.total_expenses:
            relative_cost = product.cost / benchmark.total_expenses

        impacts = Impact.query.\
            filter_by(product_id=product.id, active=True).all()
        products.append({
            'product': product,
            'impacts': impacts,
            'relative_cost': relative_cost
        })

    return products


def get_chart_pp_stacked(products, for_pdf=False):
    # Y Axis = All 17 SDGs
    # X Axis = Scale value
    # Bar color = Targeted Stakeholder, each Targeted Stakeholder group gets a unique colour

    # Stakeholder = Impact number -
    # Xaxis - Scale = Impact number -
    # all answers grouped by stakeholder, grouped by sdg

    # all data per Impact - gets consolidated into the Main SDG
    # ie Impact 1 = 6.1, 6.3 (data = 300 people)
    # result = SDG 6 += 300 (not 600)
    data = {}
    # ordered, with default value
    intensities = {str(x): [] for x in range(1, 18)}

    for product_obj in products:
        product = product_obj['product']
        for impact in product_obj['impacts']:
            # should be one stakeholder per impact
            stakeholder = ''
            answers = {}
            sdgs = []
            current_scale = 0
            sdgs_added_to = []

            for sdg in impact.sdgs:
                # can be blank??
                if sdg.sdg:
                    sdgs.append(sdg.sdg)

            for answer in impact.answers:
                answers[answer.number] = answer.data

            if stakeholder_name_question in answers:
                stakeholder = get_stakeholder_name(answers)

            stakeholder_option = answers.get(stakeholder_name_question)

            if not stakeholder_option or stakeholder_option not in individual_stakeholder_options:
                continue

            if stakeholder:
                if stakeholder not in data:
                    # put all 17 sdgs with value 0
                    data[stakeholder] = {str(x): 0 for x in range(1, 18)}

                if scale_question in answers:
                    # add the value of
                    # to all SDGs for the specific stakeholder
                    for sdg in sdgs:
                        # convert '6.a' to '6'
                        sdg = sdg.split('.')[0]
                        # answers should be an int..

                        current_scale = _get_scale(answers)

                        if current_scale and current_scale > 0 and (sdg not in sdgs_added_to):
                            sdgs_added_to.append(sdg)
                            data[stakeholder][sdg] += current_scale

            intensity = _get_intensity(answers)
            # add the score / scale(weight)
            for sdg in sdgs:
                main_sdg = sdg.split('.')[0]
                intensities[main_sdg].append({
                    'weight': current_scale,
                    'score': intensity['score']
                })

    # ordered, with default value
    calculated_intensities = {str(x): 0 for x in range(1, 18)}

    for sdg in intensities:
        weighted_score = 0
        sum_of_weights = 0

        for item in intensities[sdg]:
            sum_of_weights += item['weight']
            weighted_score += (item['score'] * item['weight'])

        if weighted_score > 0 and sum_of_weights > 0:
            final_score = weighted_score / sum_of_weights
        else:
            final_score = 0

        calculated_intensities[sdg] = round(final_score)

    chart_data = []

    for key in data:
        results = list(data[key].values())

        if sum(results) > 0:
            chart_data.append({
                'label': key,
                'data': results
            })

    return {
        'stacked': chart_data,
        'intensity': list(calculated_intensities.values()),
        'intensity_sum': sum(list(calculated_intensities.values())),
    }


def get_chart_pp_chart_2(products, for_pdf=False):
    data = []
    for product_obj in products:
        product = product_obj['product']

        for impact in product_obj['impacts']:
            # should be one stakeholder per impact
            if len(impact.answers) == 0:
                continue

            stakeholder = ''
            stakeholder_option = ''
            answers = {}
            sdgs = []
            current_scale = 0
            sdgs_added_to = []

            for sdg in impact.sdgs:
                sdgs.append(sdg.sdg)

            for answer in impact.answers:
                answers[answer.number] = answer.data

            stakeholder_option = answers.get(stakeholder_name_question)

            if not stakeholder_option or stakeholder_option in individual_stakeholder_options:
                continue

            stakeholder = get_stakeholder_name(answers)

            value_answers = get_impact_value_answers(answers)

            # add the score / scale(weight)
            unique_sdgs = list(set([x.split('.')[0] for x in sdgs]))
            sdg_obj = {x: [] for x in unique_sdgs}

            for sdg in sdgs:
                main_sdg = sdg.split('.')[0]

                sdg_obj[main_sdg].append(sdg)

            for sdg in unique_sdgs:

                intensity = _get_intensity(answers)

                data.append({
                    'stakeholder': stakeholder,
                    'sdg': "{}".format(sdg),
                    'sdg_targets': ", ".join(sdg_obj[sdg]),
                    'intensity': intensity['score'],
                    'positive_impact': impact.option_text,
                    'description': get_impact_description(impact),
                    'metric': value_answers['value'],
                    'unit': value_answers['unit'],
                })

    if data:
        data = sorted(data, key=lambda x: (utils.sdg_key(x['sdg']), x['positive_impact']))

    if for_pdf:
        data = split_additional_pages(data, 5, 30)

    return data


def get_stakeholder_name(answers):
    stakeholder_answer = answers[stakeholder_name_question]

    for q in surveys.pp_action['questions']:
        # check, as it might not be an actual question
        code = q.get('value')
        if code and code == stakeholder_name_question:
            for option in q['options']:
                if option['value'] == stakeholder_answer:
                    return option['title']


def get_impact_value_answers(answers):
    value = ''
    unit = ''

    # Scale (Customers (indi), Indirect Consumers, Employees),
    # Depth (Customers (bus), Communities/Society, Environment)

    if 'A-3' in answers:
        value = answers.get('A-3')

        # get unit
        for q in surveys.pp_action['questions']:
            code = q.get('value')
            if code and code == 'A-3':
                unit = q['unit']

    if 'A-5' in answers:

        value = answers.get('A-5')
        unit_option = answers.get('A-6')

        if unit_option in ['A-6.1', 'A-6.2']:
            # get unit
            for q in surveys.pp_action['questions']:
                code = q.get('value')
                if code and code == 'A-6':
                    for option in q['options']:
                        if option['value'] == unit_option:
                            unit = option['title']

        if unit_option == 'A-6.3':
            unit = answers.get('A-7')

    if depth_value_question in answers:
        value = answers.get(depth_value_question)
        unit = answers.get(depth_unit_question)

    if 'A-12' in answers:
        value = answers.get('A-12')
        unit = answers.get('A-13')

    return {
        'value': value,
        'unit': unit
    }


def get_chart_investment(products, for_pdf=False):
    data = []
    proposed_investment = 100000

    for product_obj in products:
        product = product_obj['product']

        for impact in product_obj['impacts']:
            answers = {a.number: a.data for a in impact.answers}

            if stakeholder_name_question in answers:
                stakeholder = get_stakeholder_name(answers)
            else:
                stakeholder = 'n/a'

            # value_answers = get_impact_value_answers(answers)
            # impact_cost = (scale/depth) / product cost
            value_answer = get_scale_or_depth(answers)

            impact_cost = 'n/a'
            if value_answer['value'] and product.cost:
                impact_cost = int(value_answer['value']) / product.cost

            if for_pdf and stakeholder == 'n/a':
                continue

            data.append({
                'name': product.name,
                'stakeholder': stakeholder,
                'impact': get_impact_description(impact),
                'cost': product.cost,
                'base_value': value_answer['value'],
                'base_unit': value_answer['unit'],
                'relative_cost': product_obj['relative_cost'],
                'impact_cost': impact_cost
            })

    res = sorted(data, key=lambda x: (x['name'], x['stakeholder']))

    if for_pdf:
        res = split_additional_pages(res, 14, 16)

    return res


def get_chart_pp_data_table(products, for_pdf=False):
    res = []
    for product_obj in products:
        product = product_obj['product']
        for impact in product_obj['impacts']:
            answers = {a.number: a.data for a in impact.answers}
            value_answers = get_impact_value_answers(answers)

            if stakeholder_name_question in answers:
                stakeholder = get_stakeholder_name(answers)
            else:
                stakeholder = 'n/a'

            impact_cost = 'n/a'
            if value_answers['value'] and product.cost:
                impact_cost = int(value_answers['value']) / product.cost

            unit = value_answers['unit']
            unit = 'n/a' if unit == '' else unit

            measurement_type = 'n/a'
            measurement_answer = answers.get('A-2')
            if measurement_answer:
                for question in surveys.pp_action['questions']:
                    if question.get('value') == 'A-2':
                        for option in question['options']:
                            if measurement_answer == option['value']:
                                measurement_type = option['title']

            # if depth_value_question in answers:
            depth_value = answers.get(depth_value_question, 'n/a')
            depth_unit = answers.get(depth_unit_question, 'n/a')
            intensity = _get_intensity(answers)

            res.append({
                'name': product.name,
                'stakeholder': stakeholder,
                'impact': get_impact_description(impact),
                'applicable': 'yes' if impact.active else 'no',
                'cost': product.cost,
                'pp_action': impact.pp_action,
                'sdgs': ', '.join([x.sdg for x in impact.sdgs]),
                'base_unit': unit,
                'measurement_type': measurement_type,
                'intensity': intensity['score'],
                'intensity_significance': intensity['significance'],
                'intensity_duration': intensity['duration'],
                'intensity_proportion': intensity['proportion'],
                'scale': _get_scale(answers),
                'depth_value': depth_value,
                'depth_unit': depth_unit,
            })

    if for_pdf:
        res = split_additional_pages(res, 16, 40)

    return res


def get_chart_be_best_and_worst(break_evens):
    filtered = [b for b in break_evens if len(b.answers) > 0 and b.applicable]
    progress = sorted(filtered, key=lambda x: x.progress_score if x.progress_score is not None else 0, reverse=True)
    progress = progress[:5]
    awareness = sorted(filtered, key=lambda x: x.awareness_score if x.awareness_score is not None else 0)
    awareness = awareness[:5]

    return {
        'awareness': [convert_best_and_worst_to_json(be) for be in awareness],
        'progress': [convert_best_and_worst_to_json(be) for be in progress],
    }


def convert_best_and_worst_to_json(be):
    scores = surveys.be[be.code]['scores']
    info = surveys.be_text_lookup['break_evens'][be.code]

    return {
        'title': info['short_name'],
        'middle_name': info['middle_name'],
        'id': be.id,
        'awareness_score': be.awareness_score,
        'awareness_unit': scores['awareness']['unit'],
        'progress_score': be.progress_score,
        'progress_unit': scores['progress']['unit'],
        'complete': len(be.answers) > 0,
        'applicable': be.applicable,
        'sdgs': surveys.be_sdgs[be.code]
    }


def get_chart_be_overview(break_evens, for_pdf=False):
    data = []
    areas = surveys.be_text_lookup['menu_items']
    lookup = {be.code: be for be in break_evens}

    for a in areas:
        area = {
            'title': a['title'],
            'items': []
        }
        for item in a['items']:
            be = lookup[item['code']]
            # if for_pdf and not be.applicable:
            #     continue
            info = surveys.be_text_lookup['break_evens'][be.code]
            scores = surveys.be[be.code]['scores']

            to_add = {
                'title': item['title'],
                'middle_name': info['middle_name'],
                'order': item['order'],
                'id': be.id,
                'awareness_score': be.awareness_score,
                'awareness_unit': scores['awareness']['unit'],
                'progress_score': be.progress_score,
                'progress_unit': scores['progress']['unit'],
                'complete': len(be.answers) > 0,
                'applicable': be.applicable,
            }

            area['items'].append(to_add)

        if for_pdf and not area['items']:
            continue
        data.append(area)

    return data


def get_scale_or_depth(answers):
    res = {
        'value': 0,
        'unit': 'n/a',
    }
    # value = 0
    # unit = 'n/a'

    if stakeholder_name_question in answers:
        stakeholder_option = answers[stakeholder_name_question]

        if stakeholder_option in individual_stakeholder_options:
            # scale
            res = {
                'value': _get_scale(answers),
                'unit': scale_depth_units[stakeholder_option]
            }
        else:
            # depth
            res = get_impact_value_answers(answers)

    return res


def _get_depth(answers):
    scale = answers.get(depth_value_question, 0)
    return int(scale) if scale else 0


def _get_scale(answers):
    scale = answers.get(scale_question, 0)
    return int(scale) if scale else 0
