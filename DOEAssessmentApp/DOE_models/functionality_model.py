from DOEAssessmentApp import db
from sqlalchemy.sql import func


class Functionality(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(), nullable=False)
    priority = db.Column(db.Integer)
    retake_assessment_days = db.Column(db.Integer)
    area_id = db.Column(db.Integer, nullable=False)
    proj_id = db.Column(db.Integer, nullable=False)
    assessmentcompletion = db.Column(db.Numeric())
    achievedpercentage = db.Column(db.Numeric())
    achievedlevel = db.Column(db.String(2))
    creationdatetime = db.Column(db.DateTime, nullable=False, server_default=func.now())
    prevassessmentcompletion = db.Column(db.Numeric())
    prevachievedpercentage = db.Column(db.Numeric())
    updationdatetime = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    createdby = db.Column(db.String(20))
    modifiedby = db.Column(db.String(20))

    def __init__(self, name, description, retake_assessment_days, area_id, proj_id, createdby, priority):
        self.name = name
        self.description = description
        self.retake_assessment_days = retake_assessment_days
        self.area_id = area_id
        self.proj_id = proj_id
        self.createdby = createdby
        self.priority = priority

    def __repr__(self):
        return '<Functionality %r>' % self.name
