from DOEAssessmentApp import db
from sqlalchemy.sql import func


class Area(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.String(), nullable=False)
    projectid = db.Column(db.Integer, nullable=False)
    assessmentcompletion = db.Column(db.Numeric())
    achievedpercentage = db.Column(db.Numeric())
    achievedlevel = db.Column(db.String(2))
    creationdatetime = db.Column(db.DateTime, nullable=False, server_default=func.now())
    prevassessmentcompletion = db.Column(db.Numeric())
    prevachievedpercentage = db.Column(db.Numeric())
    updationdatetime = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    createdby = db.Column(db.String(20))
    modifiedby = db.Column(db.String(20))

    def __init__(self, name, description, projectid, createdby):
        self.name = name
        self.description = description
        self.projectid = projectid
        self.createdby = createdby

    def __repr__(self):
        return '<Area %r>' % self.name
