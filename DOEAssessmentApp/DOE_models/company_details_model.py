from DOEAssessmentApp import db
from sqlalchemy.sql import func

# following db schema will be created in different env


class Companydetails(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    companyname = db.Column(db.String(120), nullable=False, unique=True)
    registeredaddress = db.Column(db.String(255), nullable=False)
    billingaddress = db.Column(db.String(255), nullable=False)
    registrationkey = db.Column(db.String(255), nullable=False)
    registrationkeyvalidated = db.Column(db.Integer, nullable=False, default=0)
    creationdatetime = db.Column(db.DateTime, nullable=False, server_default=func.now())
    updationdatetime = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    def __init__(self, cname, regadrs, billadrs, regkey):
        self.companyname = cname
        self.registeredaddress = regadrs
        self.billingaddress = billadrs
        self.registrationkey = regkey

    def __repr__(self):
        return '<Companydetails %r>' % self.companyname
