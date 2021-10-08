import uuid

from app import bcrypt


def reporting_period_format(benchmark):
    return "{} - {} {}".format(benchmark.month_start, benchmark.month_end, benchmark.year)


def sdg_key(key):
    if key:
        num = key.split('.')[0]
        return int(num)
    else:
        return 99999


def new_bcrypt_password(pw=None):
    if not pw:
        pw = random_uuid_code()
    return bcrypt.generate_password_hash(pw).decode('utf - 8')


def random_uuid_code(length=10):
    return str(uuid.uuid4()).replace('-', '')[0:length]


positive_pursuit_lookup = {
    "pp01": "Energy",

}


# taken from frontend
break_even_lookup = [{
    'title': 'Business Inputs',
    'path': 'business-inputs',
    'items': [
        {'path': 'be01', 'title': 'Energy', },
        {'path': 'be02', 'title': 'Water', },
        {'path': 'be03', 'title': 'Natural Resources', },
        {'path': 'be04', 'title': 'Procurement', },
    ]
},
    {
    'title': 'Operational Activities',
    'path': 'operational-activities',
    'items': [
        {'path': 'be05', 'title': 'Emissions from Operations', },
        {'path': 'be06', 'title': 'Greenhouse Gases from Operations', },
        {'path': 'be07', 'title': 'Waste Produced by Operations', },
        {'path': 'be08', 'title': 'Encroachment on Nature or Society', }
    ]
},
    {
    'title': 'Employees',
    'path': 'employees',
    'items': [
        {'path': 'be10', 'title': 'Health and Wellbeing', },
        {'path': 'be11', 'title': 'Living Wages', },
        {'path': 'be12', 'title': 'Employment Terms', },
        {'path': 'be13', 'title': 'Non-Discrimination', },
        {'path': 'be14', 'title': 'Emplyee Concerns Mechanisms', },
        {'path': 'be20', 'title': 'Ethical Conduct Within the Business', }
    ]
},
    {
    'title': 'Products',
    'path': 'products',
    'items': [
        {'path': 'be15', 'title': 'Product Communications', },
        {'path': 'be16', 'title': 'User Concerns Mechanisms', },
        {'path': 'be17', 'title': 'Potential Harm from Products', },
        {'path': 'be18', 'title': 'Greenhouse Gases from Products', },
        {'path': 'be19', 'title': 'Products can be recycled or repurposed', }
    ]
},
    {
    'title': 'Corporate Citizenship',
    'path': 'corporate-citizenship',
    'items': [
        {'path': 'be09', 'title': 'Health of Communities', },
        {'path': 'be21', 'title': 'Paying the Right Tax', },
        {'path': 'be22', 'title': 'Lobbying and Corporate Influence', },
        {'path': 'be23', 'title': 'Financial Assets', }
    ]
}

]
