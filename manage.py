"""
1. database schema create/migrate/upgrade
2. registering blueprints of endpoints
"""

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from DOEAssessmentApp import db
from flask import jsonify
from DOEAssessmentApp import app
from swagger import swagger_ui_blueprint, SWAGGER_URL
from api_spec import spec
from DOEAssessmentApp.DOE_views.email_configuration_view import emailconfig
from DOEAssessmentApp.DOE_views.rbac_view import rbac
from DOEAssessmentApp.DOE_views.company_details_view import companydetails
from DOEAssessmentApp.DOE_views.company_user_details_view import companyuserdetails
from DOEAssessmentApp.DOE_views.project_view import project
from DOEAssessmentApp.DOE_views.area_view import area
from DOEAssessmentApp.DOE_views.functionality_view import functionality_view
from DOEAssessmentApp.DOE_views.sub_functionality_view import sub_functionality_view
from DOEAssessmentApp.DOE_views.user_management_view import user_management_view
from DOEAssessmentApp.DOE_views.assessment_view import assigningteammember
from DOEAssessmentApp.DOE_views.project_assignment_to_manager_view import assigningprojectmanager
from DOEAssessmentApp.DOE_views.question_view import question
from DOEAssessmentApp.DOE_views.trn_team_member_assessment_view import assessment
from DOEAssessmentApp.DOE_views.reports_view import reports
from DOEAssessmentApp.DOE_views.audittrail_view import audittrail
from DOEAssessmentApp.DOE_views.notification_view import notific

app.register_blueprint(emailconfig)
app.register_blueprint(rbac)
app.register_blueprint(companydetails)
app.register_blueprint(companyuserdetails)
app.register_blueprint(project)
app.register_blueprint(area)
app.register_blueprint(functionality_view)
app.register_blueprint(sub_functionality_view)
app.register_blueprint(user_management_view)
app.register_blueprint(assigningteammember)
app.register_blueprint(assigningprojectmanager)
app.register_blueprint(question)
app.register_blueprint(assessment)
app.register_blueprint(reports)
app.register_blueprint(audittrail)
app.register_blueprint(notific)

# register all swagger documented functions here

with app.test_request_context():
    for fn_name in app.view_functions:
        if fn_name == 'static':
            continue
        print(f"Loading swagger docs for function: {fn_name}")
        view_fn = app.view_functions[fn_name]
        spec.path(view=view_fn)


@app.route("/api/swagger.json")
def create_swagger_spec():
    """
    Swagger API definition.
    """
    return jsonify(spec.to_dict())


app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
