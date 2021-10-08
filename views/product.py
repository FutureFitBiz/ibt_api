import re
import time
import json
import random
from datetime import datetime

from flask import jsonify, request, session
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import app, settings, db
from models import User, Company, Product, Benchmark, ProductFacet,\
    ProductProperty, ProductPropertyAnswer, Impact, ImpactSdg, ImpactAnswer
from lib.impact import surveys, get_hidden_options, get_property_actions,\
    merge_duplicate_impacts, merge_duplicate_impacts_as_list, assign_automatic_impacts,\
    get_impact_description, get_impact_description_from_dict, get_impact_percent_complete_stats,\
    get_impact_question_lookup

import utils as utils

@app.route('/product', methods=['GET'])
@jwt_required
def get_products():
    """
    get all products, and menu paths etc
    """
    # response = {'status': 'error', 'message': 'no products'}
    response = {}
    user = User.query.filter_by(email=get_jwt_identity()).first()
    benchmark = user.benchmark
    reporting_period = "{}, {} to {}".format(benchmark.year, benchmark.month_start, benchmark.month_end)

    question_lookup = get_impact_question_lookup()

    products = Product.query.\
        join(Benchmark).\
        join(User).\
        join(Company).\
        filter(User.email == get_jwt_identity()).all()

    if products:
        response = {
            'status': 'success',
            'data': []
        }
        for product in products:
            # maybe we want to show they have filled it out?
            # feel free to remove this....

            has_facets = ProductFacet.query.filter_by(product_id=product.id).count() > 0
            has_properties = ProductProperty.query.filter_by(product_id=product.id).count() > 0
            all_impacts = Impact.query.filter_by(product_id=product.id)
            current_impacts = all_impacts.filter_by(active=1).all()
            total_impacts = len(current_impacts)
            na_impacts = all_impacts.count() - total_impacts

            completed_count = 0
            impact_percent_complete = 0
            total_questions = 0
            total_answers = 0

            for impact in current_impacts:
                stats = get_impact_percent_complete_stats(question_lookup, impact.id)
                total_questions += stats['visible_questions']
                total_answers += stats['answered_questions']
                if stats['percent_complete'] == 100:
                    completed_count += 1

            if total_answers > 0 and total_questions > 0:
                impact_percent_complete = round((total_answers / total_questions) * 100)

            product_complete = (completed_count > 0) and (completed_count == total_impacts)

            menu_items = [
                {
                    'path': 'setup',
                    'title': 'Setup',
                    'complete': has_facets,
                    'percent_complete': 100 if has_facets else 0,
                },
                {
                    'path': 'identification',
                    'title': 'Identification',
                    'complete': has_properties,
                    'percent_complete': 100 if has_properties else 0,
                },
                {
                    'path': 'impacts-detailed',
                    'title': 'Impacts',
                    'complete': product_complete,
                    'percent_complete': impact_percent_complete,
                },
            ]

            has_facets_percent = 25 if has_facets else 0
            has_properties_percent = 25 if has_properties else 0
            product_impact_percent = (50 / 100) * impact_percent_complete
            product_percent_complete = has_facets_percent + has_properties_percent + product_impact_percent

            stage_name = ''
            if product.stage:
                # get the question value
                q_num = product.stage.split('.')[0]
                for q in surveys.add_edit_product['questions']:
                    if q['value'] == q_num:
                        for option in q['options']:
                            if option['value'] == product.stage:
                                stage_name = option['title']

            response['data'].append({
                'id': product.id,
                'name': product.name,
                # 'complete': product_complete,
                'percent_complete': product_percent_complete,
                'reporting_period': reporting_period,
                'description': product.description,
                'revenue_type': product.revenue_type,
                'revenue': product.revenue,
                'cost': product.cost,
                'stage': product.stage,
                'stage_name': stage_name,
                'path': product.code,
                'setup_complete': (has_facets and has_properties),
                'menu_items': menu_items,
                'total_impacts': total_impacts,
                'completed_impacts': completed_count,
                'has_facets': has_facets,
                'has_properties': has_properties,
            })

    return jsonify(response)


@app.route('/product', methods=['POST'])
@jwt_required
def add_new_product():
    data = request.json.get('data')

    email = get_jwt_identity()
    user = User.query.filter_by(email=get_jwt_identity()).first()
    benchmark = user.benchmark

    product = Product()
    product.code = utils.random_uuid_code(13)
    product.benchmark_id = benchmark.id
    product.name = data['AE-1']
    product.description = data.get('AE-2')
    product.revenue_type = data.get('AE-3')
    product.revenue = data.get('AE-4')
    product.cost = data.get('AE-5')
    product.stage = data.get('AE-6')
    product.known_costs = data.get('AE-7')
    db.session.add(product)

    db.session.commit()

    return jsonify({
        'status': 'success',
    })


@app.route('/product/<int:id>', methods=['POST'])
@jwt_required
def update_product(id):
    data = request.json.get('data')

    product = Product.query.get(id)
    product.name = data['AE-1']
    product.description = data.get('AE-2')
    product.revenue_type = data.get('AE-3')
    product.revenue = data.get('AE-4')
    product.cost = data.get('AE-5')
    product.stage = data.get('AE-6')
    product.known_costs = data.get('AE-7')
    db.session.commit()

    return jsonify({'status': 'success', })


@app.route('/product/edit/<int:id>', methods=['GET'])
@jwt_required
def get_edit_product(id):
    product = Product.query.get(id)
    answers = {
        # because of how it parses csv
        # and until we have a better way..
        'AE-1': product.name,
        'AE-2': product.description,
        'AE-3': product.revenue_type,
        'AE-4': product.revenue,
        'AE-5': product.cost,
        'AE-6': product.stage,
        'AE-7': product.known_costs,
    }
    return jsonify(answers)


@app.route('/product/delete/<int:id>', methods=['GET'])
@jwt_required
def delete_products(id):
    response = {'status': 'success'}
    product = Product.query.get(id)

    if product:
        db.session.delete(product)
        db.session.commit()
    else:
        response = {
            'status': 'error',
            'message': 'no product to delete'
        }

    return jsonify(response)


@app.route('/product/<int:product_id>/setup/<int:setup_part>/', methods=['GET'])
@jwt_required
def get_product_setup(setup_part, product_id):
    survey = {}
    checked_values = []
    hidden_options = []
    current_facets = ProductFacet.query.filter_by(product_id=product_id).all()

    if setup_part == 1:
        # we should call it something better that 'survey'.. is a remnant from surveyjs
        survey = surveys.facets
        checked_values = [x.code for x in current_facets]

    if setup_part == 2:
        survey = surveys.properties
        current_properties = ProductProperty.query.filter_by(product_id=product_id).all()
        for property in current_properties:
            checked_values.append(property.code)
            for answer in property.answers:
                checked_values.append(answer.code)

        selected_facets = ProductFacet.query.filter_by(product_id=product_id).all()
        selected_facet_codes = [x.code for x in selected_facets]

        questions = surveys.properties['questions'][1:]

        for question in questions:
            if question['type'] == 'checkbox':
                hidden_options += get_hidden_options(question['options'], selected_facet_codes)

    response = {
        'status': 'success',
        'data': {
            'has_facets': len(current_facets) > 0,
            'survey': survey,
            'checked_values': checked_values,
            'hidden_options': hidden_options
        }
    }

    return jsonify(response)


@app.route('/product/<int:product_id>/setup/<int:setup_part>/preview', methods=['POST'])
@jwt_required
def preview_changes(setup_part, product_id):
    data = request.json.get('data')

    # ADDING IMPACT TO THE IMPACTS
    if not settings.DEBUG:
        time.sleep(1.6)

    changes = {
        'facets': {
            'deleted': [],
            'added': []
        },
        'properties': []
    }

    updated_facets = []
    updated_properties = {}

    # check facets
    current_facets = ProductFacet.query.filter_by(product_id=product_id).all()
    if setup_part == 1:
        updated_facets = data
        # get current selected facets
        current_facet_codes = [x.code for x in current_facets]

        for code in data:
            if code not in current_facet_codes:
                changes['facets']['added'].append({
                    'code': code,
                    'description': surveys.facet_description_lookup.get(code)
                })

        for facet in current_facets:
            if facet.code not in data:
                changes['facets']['deleted'].append({
                    'code': facet.code,
                    'description': surveys.facet_description_lookup.get(facet.code)
                })

        # now load answers
        current_properties = ProductProperty.query.filter_by(product_id=product_id).all()
        for property in current_properties:
            product_answers = ProductPropertyAnswer.query.\
                filter_by(product_property_id=property.id).\
                order_by(ProductPropertyAnswer.code).all()

            updated_properties[property.code] = [x.code for x in product_answers]
    else:
        # no changes to facets so updated are just current...
        updated_facets = [x.code for x in current_facets]

        # add keys / properties first
        # filter out the ones that are X, vs X1- to X8-
        # the X anwers ie, 'X2' will un hide the section X2 - Water
        # so we can use these as main keys

        # ugh, so now we are processing them all teh same wayyyy
        # X3 becomes X-1.3

        for code in data:
            tokens = code.split('-')
            x = tokens[0]
            if len(x) == 1:
                updated_properties[code] = []

        # now the questions
        for code in data:
            tokens = code.split('-')
            x = tokens[0]
            if len(x) == 2:
                # get the value of the X tab
                num = list(x)[1]
                # convert it back to how it gets parsed..
                converted_code = 'X-1.' + num
                if converted_code in updated_properties:
                    updated_properties[converted_code].append(code)

        current_properties = ProductProperty.query.filter_by(product_id=product_id).all()
        current_property_codes = [x.code for x in current_properties]

        for property in current_properties:
            add_me = {
                'added': [],
                'deleted': [],
                'name': surveys.property_title_lookup.get(property.code, '_')
            }

            if property.code in updated_properties:
                current_answer_codes = [x.code for x in property.answers]

                for new_answer in updated_properties[property.code]:
                    if new_answer not in current_answer_codes:
                        add_me['added'].append({
                            'code': new_answer,
                            'description': surveys.property_description_lookup[new_answer]
                        })

                for answer in property.answers:
                    if answer.code not in updated_properties[property.code]:
                        add_me['deleted'].append({
                            'code': answer.code,
                            'description': surveys.property_description_lookup[answer.code]
                        })
            else:
                add_me['deleted'].append({
                    'code': property.code,
                    'description': 'all'
                    # if they are deleting the area, all options will be removed
                    # 'description': surveys.property_title_lookup[property.code]
                })

            if len(add_me['deleted']) > 0 or len(add_me['added']) > 0:
                changes['properties'].append(add_me)

        for code in updated_properties.keys():
            if code not in current_property_codes:
                add_me = {
                    'added': [],
                    'deleted': [],
                    'name': surveys.property_title_lookup[code]
                }

                for answer in updated_properties[code]:
                    add_me['added'].append({
                        'code': answer,
                        'description': surveys.property_description_lookup[answer]
                    })

                changes['properties'].append(add_me)

    # great we have done this all, lets calculate the actions if it is the second setup
    impact_changes = calculate_impacts(updated_facets, updated_properties, product_id)

    return jsonify({
        'status': 'success',
        'data': {
            'impacts': impact_changes,
            'properties': changes['properties'],
            'facets': changes['facets']
        }
    })


@app.route('/product/<int:product_id>/setup/<int:setup_part>/', methods=['POST'])
@jwt_required
def save_setup(setup_part, product_id):
    data = request.json.get('data')

    # ADDING IMPACT TO THE IMPACTS
    if not settings.DEBUG:
        time.sleep(1.1)

    updated_facets = None
    updated_properties = {}

    # save facets
    # get current selected facets
    current_facets = ProductFacet.query.filter_by(product_id=product_id).all()

    if setup_part == 1:
        current_facet_codes = [x.code for x in current_facets]

        for code in data:
            if code not in current_facet_codes:
                add = ProductFacet()
                add.product_id = product_id
                add.code = code
                db.session.add(add)

        for facet in current_facets:
            if facet.code not in data:
                db.session.delete(facet)

        # now load answers
        properties = ProductProperty.query.filter_by(product_id=product_id).all()
        for property in properties:
            product_answers = ProductPropertyAnswer.query.filter_by(
                product_property_id=property.id).order_by(ProductPropertyAnswer.code).all()

            updated_properties[property.code] = [x.code for x in product_answers]

        # use the new facets when calculating impacts later
        updated_facets = data

    # save properties
    else:
        updated_facets = [x.code for x in current_facets]

        # add keys / properties first
        # filter out the ones that are X, vs X1- to X8-
        # the X anwers ie, 'X2' will un hide the section X2 - Water
        # so we can use these as main keys

        # ugh, so now we are processing them all teh same wayyyy
        # X3 becomes X-1.3

        for code in data:
            tokens = code.split('-')
            x = tokens[0]
            if len(x) == 1:
                updated_properties[code] = []

        # now the questions
        for code in data:
            tokens = code.split('-')
            x = tokens[0]
            if len(x) == 2:
                # get the value of the X tab
                num = list(x)[1]
                # convert it back to how it gets parsed..
                converted_code = 'X-1.' + num
                updated_properties[converted_code].append(code)

        current_properties = ProductProperty.query.filter_by(product_id=product_id).all()
        current_property_codes = [x.code for x in current_properties]

        for property in current_properties:
            if property.code in updated_properties:
                current_answer_codes = [x.code for x in property.answers]

                for new_answer in updated_properties[property.code]:
                    if new_answer not in current_answer_codes:
                        sa = ProductPropertyAnswer()
                        sa.product_property_id = property.id
                        sa.code = new_answer
                        db.session.add(sa)

                for answer in property.answers:
                    if answer.code not in updated_properties[property.code]:
                        db.session.delete(answer)
            else:
                db.session.delete(property)

        for property in updated_properties.keys():
            if property not in current_property_codes:
                pp = ProductProperty()
                pp.product_id = product_id
                pp.code = property
                db.session.add(pp)
                for answer in updated_properties[property]:
                    sa = ProductPropertyAnswer()
                    sa.code = answer
                    pp.answers.append(sa)

        # great we have done this all, lets calculate the actions if it is the second setup
        impact_changes = calculate_impacts(updated_facets, updated_properties, product_id)

    db.session.commit()

    return jsonify({'status': 'success'})


def get_parent_property(code):
    res = code
    dots = code.count('.')
    if dots > 1:
        res = code.split('.')[0]
    return res



def calculate_impacts(facet_codes, properties, product_id):
    # Go through the answered surveys for the product and get the recommended actions
    # get current selected facets
    changes = {}
    impacts = []

    # property = X1, X2, etc
    for property_code in properties.keys():
        answers = sorted(properties[property_code])
        impacts += get_property_actions(answers, property_code, facet_codes)

    impacts = assign_automatic_impacts(impacts, facet_codes)
    impacts = merge_duplicate_impacts(impacts)

    # TODO: uhh be more efficent at deleting, only remove what has changed...
    # this is fastest for now!
    current_impacts = Impact.query.filter_by(product_id=product_id).all()
    existing_impacts = []

    for ci in current_impacts:
        key = ci.option_text + ci.pp_action
        existing_impacts.append(key)

        impact_info = {
            'property_code': ci.property_code,
            'option_text': ci.option_text,
            'pp': ci.pp_action
        }

        property = get_parent_property(ci.property_code)

        if property not in changes:
            # if there's no code.. its probably an 'automatic', ie x-0 impact - or its broke af again
            name = surveys.property_title_lookup[ci.property_code]

            changes[property] = {
                'deleted': [],
                'added': [],
                'modified': [],
                'name': name
            }

        if key not in impacts:
            changes[property]['deleted'].append({
                'code': ci.property_code,
                'text': ci.option_text,
                'sdgs': ', '.join([x.sdg for x in ci.sdgs])
            })

            db.session.delete(ci)
        else:
            modified = False
            updated_impact = impacts[key]
            existing_sdgs = []
            for sdg in ci.sdgs:
                if sdg.sdg not in updated_impact['sdgs']:
                    modified = True
                    db.session.delete(sdg)
                else:
                    existing_sdgs.append(sdg.sdg)

            for sdg in updated_impact['sdgs']:
                if sdg not in existing_sdgs:
                    modified = True
                    sdg_add = ImpactSdg()
                    sdg_add.sdg = sdg
                    db.session.add(sdg_add)
                    ci.sdgs.append(sdg_add)

            if modified:
                changes[property]['modified'].append({
                    'sdgs': ','.join(updated_impact['sdgs']),
                    'code': updated_impact['property_code'],
                    'text': updated_impact['option_text']
                })

    for key in impacts:
        if key not in existing_impacts:
            impact = impacts[key]
            add = Impact()
            add.property_code = impact['property_code']
            add.option_text = impact['option_text']
            add.option_code = impact['option_code']
            add.pp_action = impact['pp']
            add.product_id = product_id
            db.session.add(add)

            for sdg in impact['sdgs']:
                if sdg:
                    # get rid of blank ones
                    sdg_add = ImpactSdg()
                    sdg_add.sdg = sdg
                    db.session.add(sdg_add)
                    add.sdgs.append(sdg_add)

            property = get_parent_property(impact['property_code'])

            if property not in changes:
                changes[property] = {
                    'deleted': [],
                    'added': [],
                    'modified': [],
                    'name': surveys.property_description_lookup[property]
                }

            changes[property]['added'].append({
                'sdgs': ', '.join(impact['sdgs']),
                'code': impact['property_code'],
                'pp': impact['pp'],
                'text': get_impact_description_from_dict(impact)
            })

    return changes



@app.route('/product/<int:product_id>/property/stats', methods=['POST'])
@jwt_required
def get_property_stats(product_id):
    data = request.json.get('data')

    current_properties = ProductProperty.query.filter_by(product_id=product_id).all()
    for property in current_properties:
        for answer in property.answers:
            pass

    return jsonify({'status': 'success'})

@app.route('/product/<int:product_id>/impacts', methods=['GET'])
@jwt_required
def get_product_impacts(product_id):
    impacts = []
    question_lookup = get_impact_question_lookup()

    current_impacts = Impact.query.filter_by(product_id=product_id).all()

    for i, current_impact in enumerate(current_impacts, 1):
        # # TODO: go through and add the full option list
        # ie, "Energy > Some option > Some suboption that you clicked"
        sdgs = [x.sdg for x in current_impact.sdgs if x.sdg != '']
        sdgs = sorted(sdgs, key=lambda x: utils.sdg_key(x))
        sdgs = ', '.join(sdgs)

        completed_stats = get_impact_percent_complete_stats(question_lookup, current_impact.id)

        impacts.append({
            'number': i,
            'id': current_impact.id,
            'pp': current_impact.pp_action,
            'property_code': current_impact.property_code,
            'option': current_impact.option_code,
            'text': current_impact.option_text,
            'active': current_impact.active,
            'completed': completed_stats['percent_complete'] == 100,
            'description': get_impact_description(current_impact),
            'pp_text': surveys.pp_text_lookup[current_impact.pp_action],
            'sdgs': sdgs,
            'visible_questions': completed_stats['visible_questions'],
            'percent_complete': completed_stats['percent_complete'],
            'answered_questions': completed_stats['answered_questions']
        })

    response = {
        'actions': impacts,
    }

    return jsonify(response)


@app.route('/product/<int:product_id>/impact/<int:impact_id>', methods=['GET'])
@jwt_required
def get_action_data(product_id, impact_id):
    # get the current answers for the action_id - what the name says!
    answers = {}
    external_answers = {}

    current_answers = ImpactAnswer.query.filter_by(impact_id=impact_id).all()
    for answer in current_answers:
        answers[answer.number] = answer.text if answer.text else answer.data

    return jsonify({
        'answers': answers,
    })


@app.route('/product/<int:product_id>/impact/<int:impact_id>', methods=['POST'])
@jwt_required
def save_action_data(product_id, impact_id):
    data = request.json.get('data')
    current_answers = ImpactAnswer.query.filter_by(impact_id=impact_id).all()
    for current_answer in current_answers:
        db.session.delete(current_answer)

    for key in data['answers'].keys():
        #only add if there is actual data
        if len(data['answers'][key]) > 0:
            add = ImpactAnswer()
            add.impact_id = impact_id
            add.number = key
            # check the question type
            type = get_impact_question_type(key)
            if type == 'text area':
                add.text = data['answers'][key]
                pass
            else:
                add.data = data['answers'][key]

            db.session.add(add)

    db.session.commit()

    return jsonify({
        'success': True,
    })


def get_impact_question_type(key):
    for question in surveys.pp_action['questions']:
        value = question.get('value')
        if value and value == key:
            return question.get('type')

@app.route('/product/impact/<int:impact_id>/set_active/<active>', methods=['POST'])
@jwt_required
def toggle_impact_active(impact_id, active):
    impact = Impact.query.filter_by(id=impact_id).one()
    impact.active = (active == 'true')
    db.session.commit()

    return jsonify({
        'success': True,
    })
