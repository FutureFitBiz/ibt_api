from app import db


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(80), nullable=False)
    intro_complete = db.Column(db.Boolean, nullable=False, default=False)
    description = db.Column(db.Text, nullable=True)
    industry_type = db.Column(db.String(120), nullable=True)
    business_model = db.Column(db.String(120), nullable=True)
    hidden = db.Column(db.Boolean, nullable=False, default=False)
    logo = db.Column(db.BLOB, nullable=True)
    logo_file_extension = db.Column(db.String(20), nullable=True)

    users = db.relationship('User', backref='company', lazy=True)
    benchmarks = db.relationship('Benchmark', backref='company', cascade="all,delete", lazy=True)

    def __repr__(self):
        return '<Company %r>' % self.name


class Benchmark(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    approved = db.Column(db.Boolean, default=False)
    approved_on = db.Column(db.Float(53), nullable=True)
    year = db.Column(db.String(4), nullable=False)
    month_start = db.Column(db.String(12), nullable=True)
    month_end = db.Column(db.String(12), nullable=True)
    total_revenue = db.Column(db.Float, nullable=True)
    total_expenses = db.Column(db.Float, nullable=True)

    products = db.relationship('Product', backref='benchmark', cascade="all,delete", lazy=True)
    break_evens = db.relationship('BreakEven', backref='benchmark', cascade="all,delete", lazy=True)
    users = db.relationship('User', backref='benchmark', lazy=True)

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)


class BreakEven(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(20), nullable=True)
    progress_score = db.Column(db.Float, nullable=True, default=0)
    awareness_score = db.Column(db.Float, nullable=True, default=0)
    applicable = db.Column(db.Boolean, nullable=True)

    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmark.id'), nullable=True)
    answers = db.relationship('BreakEvenAnswer', backref="break_even", cascade="all,delete", lazy='subquery')

    def __repr__(self):
        return '<BreakEven %r>' % self.code


class BreakEvenAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    break_even_id = db.Column(db.Integer, db.ForeignKey('break_even.id'))
    # ie the question code, eg A-2
    code = db.Column(db.String(20), nullable=False)
    # the answer eg A-2.1, or 'potatos', or whatever
    data = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return '<BreakEvenAnswer %r>' % self.code


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20), nullable=True)
    type = db.Column(db.String(120), nullable=True)
    cost = db.Column(db.Float, nullable=True)
    revenue_type = db.Column(db.String(20), nullable=True)
    revenue = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    known_costs = db.Column(db.String(20), nullable=True)

    # eg AE-6.3 =  Scaling up
    stage = db.Column(db.String(20), nullable=True)

    percent_complete = db.Column(db.Integer, default=0)

    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmark.id'), nullable=True)
    impacts = db.relationship('Impact', backref="product",  cascade="all,delete")
    facets = db.relationship('ProductFacet', backref="product",  cascade="all,delete")
    product_properties = db.relationship('ProductProperty', backref="product",  cascade="all,delete")

    def __repr__(self):
        return '<Product %r>' % self.name


class ProductFacet(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(80), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))


class ProductProperty(db.Model):
    """
    property - refers to the 'Properties' tab, ie X, X1, X2, etc
    ie, this is a link between the Product & all the Identification answers
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(80), nullable=False)  # property code
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))

    answers = db.relationship('ProductPropertyAnswer',cascade="all,delete", backref="product_property")

    def __repr__(self):
        return '<ProductProperty %r>' % self.code


class ProductPropertyAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(80), nullable=False)
    product_property_id = db.Column(db.Integer, db.ForeignKey('product_property.id'))


class Impact(db.Model):
    """
    so, it's unique on PP action + Option text (not the option number)
    the result of doing Setup & 2 and then having your actions mapped
    save pp action, text, SDGs
    where do we want to save the data from the survey that links to this tho?
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))

    property_code = db.Column(db.String(80), nullable=False)  # property code
    pp_action = db.Column(db.String(80), nullable=False)  # ie PP01.01
    option_code = db.Column(db.String(80), nullable=False)
    option_text = db.Column(db.String(500), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    sdgs = db.relationship('ImpactSdg', backref="impact",  cascade="all,delete")
    answers = db.relationship('ImpactAnswer', backref="impact", cascade="all,delete", lazy='subquery')


class ImpactSdg(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sdg = db.Column(db.String(80), nullable=False)
    impact_id = db.Column(db.Integer, db.ForeignKey('impact.id'))


class ImpactAnswer(db.Model):
    """
    so, it's unique on PP action + Option text (not the option number)
    the result of doing Setup & 2 and then having your actions mapped
    save pp action, text, SDGs
    where do we want to save the data from the survey that links to this tho?
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    impact_id = db.Column(db.Integer, db.ForeignKey('impact.id'))
    number = db.Column(db.String(20), nullable=False)
    data = db.Column(db.String(200), nullable=True)  # going to be code or the number or string
    text = db.Column(db.Text, nullable=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    password = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    first = db.Column(db.String(120), nullable=True)
    last = db.Column(db.String(120), nullable=True)
    welcome = db.Column(db.Boolean, nullable=True, default=False)
    admin = db.Column(db.Boolean, nullable=True, default=False)
    investor = db.Column(db.Boolean, nullable=True, default=False)
    benchmark_id = db.Column(db.Integer, db.ForeignKey('benchmark.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=True)

    def __repr__(self):
        return '<User %r>' % self.email
