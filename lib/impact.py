from lib.csv_parser import Surveys
from models import ImpactAnswer

surveys = Surveys()
surveys.load()

def get_impact_percent_complete_stats(question_lookup, impact_id):
    #run through the answers and see if we have answerd all that is visible - based on the answers
    answers = {}
    stats = {}
    visible_questions = 0
    answered_questions = 0
    percent_complete = 0

    current_answers = ImpactAnswer.query.filter_by(impact_id=impact_id).all()
    for current_answer in current_answers:
        answers[current_answer.number] = current_answer.data

    for number in question_lookup:
        question = question_lookup[number]
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

def get_impact_question_lookup():
    #get the questions so we can see if all that is needed
    questions = surveys.pp_action['questions'][1:] #we ignore the first one...????
    question_lookup = {}
    for question in questions:
        if 'number' in question:
            question_lookup[question['value']] = question

    return question_lookup

def get_impact_description(impact):
    description_key = "{}-{}".format(impact.pp_action, impact.option_code)
    description = surveys.pp_descriptions.get(description_key, 'Description missing')
    return description

def get_impact_description_from_dict(impact):
    """used in calculating preview impacts"""
    description_key = "{}-{}".format(impact['pp'], impact['option_code'])
    description = surveys.pp_descriptions.get(description_key, 'Description missing')
    return description


def merge_duplicate_impacts(actions):
    # now we de-dup the actions:
    """
    so, we've already merged the blank ones,
    and ones further up in the tree of that specific option,
    this is merging duplicates from across different main options & x tabs
    """
    impacts = {}

    for action in actions:
        key = action['option_text'] + action['pp']

        if key not in impacts:
            impacts[key] = action
        else:
            impacts[key]['sdgs'] += action['sdgs']

    # merge all SDGs per impact
    for key in impacts:
        sdgs = impacts[key]['sdgs']
        sdgs = [x for x in sdgs if x not in ['', ' ', ',']]
        impacts[key]['sdgs'] = list(set(impacts[key]['sdgs']))

    return impacts


def merge_duplicate_impacts_as_list(actions):
    """
    thing for kev, list of unique combos
    """
    impacts = {}

    for action in actions:
        key = action['option_text'] + action['pp']

        if key not in impacts:
            impacts[key] = action
        else:
            impacts[key]['sdgs'] += action['sdgs']

    # merge all SDGs per impact
    for key in impacts:
        sdgs = impacts[key]['sdgs']
        sdgs = [x for x in sdgs if x != '']
        impacts[key]['sdgs'] = list(set(impacts[key]['sdgs']))

    list_impacts = []
    for key in impacts:
        list_impacts.append(impacts[key])

    return list_impacts


def get_hidden_options(options, selected_facets):
    ret = []
    for option in options:
        # check the current option
        if option.get('facets'):
            match = _check_f_logic(option['facets'], selected_facets)
            if not match:
                ret.append(option['value'])

        # recursively check all sub options
        if option.get('options'):
            ret += get_hidden_options(option['options'], selected_facets)

    return ret


def assign_automatic_impacts(impacts, selected_facets):
    """
    if they have the facets, but not the action:
        add a new impact from the automatics
    """
    # get all the pp actions from the current impact list
    pps = []
    for i in impacts:
        if i['pp'] not in pps:
            pps.append(i['pp'])

    for index, x in enumerate(surveys.x0):
        for action in x['actions']:
            if action['pp'] not in pps:
                add = True
                # check facets
                for f in action['facets']:
                    if f not in selected_facets:
                        add = False
                        break

                if add:
                    # duplicates are merged in the next step after
                    impacts.append({
                        'pp': action['pp'],
                        'sdgs': action['sdgs'],
                        'option_code': x['value'],
                        'option_text': x['title'],
                        'property_code': 'X-0'
                    })

    return impacts


def get_property_actions(answers, property_code, selected_facets):
    """
    generate a list of actions (that will get merged into impacts later on)
    take the answers from the frontend, and loop through the parsed csv
    """
    actions = []

    all_property_questions = surveys.properties['questions']
    property_questions = None

    # get all the questions for a section
    for question in all_property_questions:
        # we're using 'logic' just to get the main code ie 'X-1.7' ie, tab X7
        logic = question.get('logic')
        if logic:
            # take it out of the [[]] we use for AND/OR allocation
            logic = logic[0][0]

        if logic and question['type'] == 'checkbox' and logic == property_code:
            property_questions = question
            break

    for answer in answers:
        answer_actions = _get_answer_actions(property_questions['options'], selected_facets, answer, property_code)
        if answer_actions:
            actions += answer_actions

    actions = _update_actions_per_option_tree(actions)

    return actions


def _update_actions_per_option_tree(actions):
    """
    so when we have a sub option, it gets all of the actions/sdgs from the further up options..
    eg [1.1, 1.1.1] => 1.1.1 (and take sdgs/actions from 1.1)
    also
    eg [1.1, 1.1.1, 1.1.2] => 1.1.1 & 1.1.2 both get sdgs/actions from 1.1

    first we need to find the sub most option
    (there could be multiple at the same level),
    then take all the previous ones
    (one action may be added multiple times with different text)
    and duplicate the options and put the text on all that link to it,
    """
    action_codes = [x['option_code'] for x in actions]
    grouped_codes = _group_by_reverse_sub_options(action_codes)
    new_actions = []

    for key in grouped_codes:

        text = ''
        # find the main ones
        for a in actions:
            if a['option_code'] == key:
                # action = a
                new_actions.append(a)
                if a['option_text']:
                    text = a['option_text']

        codes = grouped_codes[key]

        for a in actions:
            if a['option_code'] in codes:
                b = a.copy()
                b['option_text'] = text
                new_actions.append(b)

    return new_actions


def _group_by_reverse_sub_options(codes):
    """
    make a dict of the lowest sub options, with all its previous options attached
    *and chop out all of the other options
    eg:
    original = [3, 3.1, 3.1.1, 3.1.2]
    {
        '3.1.1': [3, 3.1],
        '3.1.2': [3, 3.1]
    }
    so we have a list of what actions to pull down into the sub option
    """
    res = {}

    for c in codes:
        sub_codes = _get_sub_codes(c)

        res[c] = sub_codes
        # remove codes if the are now part of a sub option
        for sc in sub_codes:
            if sc in res:
                del res[sc]

    return res


def _get_sub_codes(c):
    previous_codes = []
    tokens = c.split('.')

    for (i, token) in enumerate(tokens[1:], 1):
        previous_codes.append(".".join(tokens[:i]))

    return previous_codes


def _check_f_logic(facets, selected_facets):
    # this can be OR
    f2s_action = [x for x in facets if x[2] == '2']
    f2s_selected = [x for x in selected_facets if x[2] == '2']

    # this must be all
    fs_action = [x for x in facets if x[2] != '2']
    fs_selected = [x for x in selected_facets if x[2] != '2']

    matches = [x in fs_selected for x in fs_action]

    if f2s_action:
        f2_result = any([x in f2s_selected for x in f2s_action])
        matches.append(f2_result)

    return all(matches)


def _get_answer_actions(options, selected_facets, answer, property_code):
    ret = []

    for option in options:
        if option['value'] == answer:
            ret = []
            for action in option['actions']:
                match = True

                if action['facets']:
                    match = _check_f_logic(action['facets'], selected_facets)

                if match:
                    ret.append({
                        'pp': action['pp'],
                        'sdgs': [x for x in action['sdgs']],
                        'property_code': property_code,
                        'option_text': option['title'],
                        'option_code': option['value']
                    })

            return ret
        elif len(option['options']) > 0:
            ret += _get_answer_actions(option['options'], selected_facets, answer, property_code)

    return ret
