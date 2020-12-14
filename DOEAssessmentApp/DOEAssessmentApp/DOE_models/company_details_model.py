import datetime
from DOEAssessmentApp import db

# following db schema will be created in different env


class Companydetails(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    companyname = db.Column(db.String(120), nullable=False, unique=True)
    registeredaddress = db.Column(db.String(255), nullable=False)
    billingaddress = db.Column(db.String(255), nullable=False)
    gstortaxnumber = db.Column(db.String(120), nullable=False, unique=True)
    registrationkey = db.Column(db.String(255), nullable=False)
    registrationkeyvalidated = db.Column(db.Integer, nullable=False, default=0)
    creationdatetime = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)

    def __init__(self, cname, regadrs, billadrs, gst, regkey):
        self.companyname = cname
        self.registeredaddress = regadrs
        self.billingaddress = billadrs
        self.gstortaxnumber = gst
        self.registrationkey = regkey

    def __repr__(self):
        return '<Companydetails %r>' % self.companyname
