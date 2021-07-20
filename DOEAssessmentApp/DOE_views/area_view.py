from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.project_model import Project
from DOEAssessmentApp.DOE_models.area_model import Area
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

area = Blueprint('area', __name__)

cols_subfunc = ['id', 'name', 'description', 'retake_assessment_days', 'func_id', 'area_id', 'proj_id',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']

colsquestion = ['id', 'name', 'answer_type', 'answers', 'maxscore', 'subfunc_id', 'func_id', 'area_id', 'proj_id',
                'combination', 'mandatory', 'islocked', 'isdependentquestion',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@area.route('/api/area', methods=['GET', 'POST'])
def getaddarea():
    """
        ---
        get:
          description: Fetch area(s).
          parameters:
            -
              name: Authorization
              in: header
              type: string
              required: true
          responses:
            '200':
              description: call successful
              content:
                application/json:
                  schema: OutputSchema
          tags:
              - getcreatearea
        post:
          description: Create an area.
          parameters:
            -
              name: Authorization
              in: header
              type: string
              required: true
          requestBody:
            required: true
            content:
                application/json:
                    schema: InputSchema
          responses:
            '200':
              description: call successful
              content:
                application/json:
                  schema: OutputSchema
          tags:
              - getcreatearea
    """
    try:
        results = []
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "GET":
                    data = Area.query.all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'priority': d.priority},
                                              {'projectid': d.projectid},
                                              {'assessmentcompletion': str(d.assessmentcompletion)},
                                              {'achievedpercentage': str(d.achievedpercentage)},
                                              {'achievedlevel': d.achievedlevel},
                                              {'creationdatetime': d.creationdatetime},
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    areaname = res['name']
                    areadesc = res['description']
                    priority = res['priority']
                    proj_id = res['projectid']
                    existing_area = Area.query.filter(Area.name == areaname, Area.projectid == proj_id).one_or_none()

                    projectmanager = Projectassignmenttomanager.query.filter_by(project_id=proj_id)
                    if projectmanager.first() is not None:
                        empid = projectmanager.first().emp_id
                        userdata = Companyuserdetails.query.filter_by(empid=empid).first()
                        empname = userdata.empname
                        companyid = userdata.companyid
                        mailto = userdata.empemail
                        emailconf = Emailconfiguration.query.filter_by(companyid=companyid).first()
                        if emailconf.email == 'default' and emailconf.host == 'default' \
                                and emailconf.password == 'default':
                            mailfrom = app.config.get('FROM_EMAIL')
                            host = app.config.get('HOST')
                            pwd = app.config.get('PWD')
                        else:
                            mailfrom = emailconf.email
                            host = emailconf.host
                            pwd = emailconf.password

                        # region mail notification
                        notification_data = Notification.query.filter_by(
                            event_name="ADDAREATOMANAGER").first()
                        mail_subject = notification_data.mail_subject
                        mail_body = str(notification_data.mail_body).format(empname=empname, areaname=areaname)
                        mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region

                    if existing_area is None:
                        areains = Area(areaname, areadesc, proj_id, session['empid'], priority)
                        db.session.add(areains)
                        db.session.commit()

                        data = Area.query.filter_by(id=areains.id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'projectid': d.projectid},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        # region call audit trail method
                        auditins = Audittrail("AREA", "ADD", None, str(results[0]), session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": f"Area {areaname} has been successfully added.",
                                                      "data": results[0]})), 201
                    else:
                        data_proj = Project.query.filter_by(id=proj_id).first()
                        return make_response(jsonify({"msg": f"Area {areaname} already "
                                                             f"exists for project {data_proj.name}."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@area.route('/api/updelarea/', methods=['POST', 'PUT', 'DELETE'])
def updelarea():
    """
        ---
        post:
          description: Fetch an area.
          parameters:
            -
              name: Authorization
              in: header
              type: string
              required: true
          requestBody:
            required: true
            content:
                application/json:
                    schema: InputSchema
          responses:
            '200':
              description: call successful
              content:
                application/json:
                  schema: OutputSchema
          tags:
              - updatedeletearea
        put:
          description: Update an area.
          parameters:
            -
              name: Authorization
              in: header
              type: string
              required: true
          requestBody:
            required: true
            content:
                application/json:
                    schema: InputSchema
          responses:
            '200':
              description: call successful
              content:
                application/json:
                  schema: OutputSchema
          tags:
              - updatedeletearea
        delete:
          description: Delete an area.
          parameters:
            -
              name: Authorization
              in: header
              type: string
              required: true
          requestBody:
            required: true
            content:
                application/json:
                    schema: InputSchema
          responses:
            '200':
              description: call successful
              content:
                application/json:
                  schema: OutputSchema
          tags:
              - updatedeletearea
    """
    try:
        results = []
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                res = request.get_json(force=True)
                areaid = res['areaid']
                data = Area.query.filter_by(id=areaid)
                for d in data:
                    json_data = mergedict({'id': d.id},
                                          {'name': d.name},
                                          {'description': d.description},
                                          {'priority': d.priority},
                                          {'projectid': d.projectid},
                                          {'assessmentcompletion': str(d.assessmentcompletion)},
                                          {'achievedpercentage': str(d.achievedpercentage)},
                                          {'achievedlevel': d.achievedlevel},
                                          {'creationdatetime': d.creationdatetime},
                                          {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                          {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                          {'updationdatetime': d.updationdatetime},
                                          {'createdby': d.createdby},
                                          {'modifiedby': d.modifiedby})
                    results.append(json_data)
                areadatabefore = results[0]
                results.clear()
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect ID"})), 404
                else:
                    if request.method == 'POST':
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'projectid': d.projectid},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        return jsonify({"data": results[0]})
                    if request.method == 'PUT':
                        areadesc = res['AreaDescription']
                        priority = res['priority']
                        data.first().description = areadesc
                        data.first().priority = priority
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()
                        data = Area.query.filter_by(id=areaid)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'projectid': d.projectid},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        areadataafter = results[0]
                        # region call audit trail method
                        auditins = Audittrail("AREA", "UPDATE", str(areadatabefore), str(areadataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"message": f"Area {data.first().name} successfully "
                                                                 f"updated."})), 200

                    elif request.method == 'DELETE':

                        projectmanager = Projectassignmenttomanager.query.filter_by(project_id=data.first().projectid)
                        if projectmanager.first() is not None:
                            userdata = Companyuserdetails.query.filter_by(empid=projectmanager.first().emp_id).first()
                            empname = userdata.empname
                            companyid = userdata.companyid
                            mailto = userdata.empemail
                            emailconf = Emailconfiguration.query.filter_by(companyid=companyid).first()
                            if emailconf.email == 'default' and emailconf.host == 'default' \
                                    and emailconf.password == 'default':
                                mailfrom = app.config.get('FROM_EMAIL')
                                host = app.config.get('HOST')
                                pwd = app.config.get('PWD')
                            else:
                                mailfrom = emailconf.email
                                host = emailconf.host
                                pwd = emailconf.password

                            # region mail notification
                            notification_data = Notification.query.filter_by(
                                event_name="DELETEAREATOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                areaname=data.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("AREA", "DELETE", str(areadatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region

                        data_func = Functionality.query.filter_by(area_id=areaid)
                        if data_func is not None:
                            for f in data_func:
                                json_data = mergedict({'id': f.id},
                                                      {'name': f.name},
                                                      {'description': f.description},
                                                      {'priority': f.priority},
                                                      {'retake_assessment_days': f.retake_assessment_days},
                                                      {'area_id': f.area_id},
                                                      {'proj_id': f.proj_id},
                                                      {'assessmentcompletion': str(f.assessmentcompletion)},
                                                      {'achievedpercentage': str(f.achievedpercentage)},
                                                      {'achievedlevel': f.achievedlevel},
                                                      {'creationdatetime': f.creationdatetime},
                                                      {'prevassessmentcompletion': str(f.prevassessmentcompletion)},
                                                      {'prevachievedpercentage': str(f.prevachievedpercentage)},
                                                      {'updationdatetime': f.updationdatetime},
                                                      {'createdby': f.createdby},
                                                      {'modifiedby': f.modifiedby})
                                results.append(json_data)
                                db.session.delete(f)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("FUNCTIONALITY", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        data_subfunc = Subfunctionality.query.filter_by(area_id=areaid)
                        if data_subfunc is not None:
                            for s in data_subfunc:
                                data = Subfunctionality.query.filter_by(id=s.id)
                                results = [{col: getattr(d, col) for col in cols_subfunc} for d in data]
                                db.session.delete(s)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("SUB-FUNCTIONALITY", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        data_question = Question.query.filter_by(area_id=areaid)
                        if data_question is not None:
                            for q in data_question:
                                data = Question.query.filter_by(id=q.id)
                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                db.session.delete(q)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("QUESTION", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        return make_response(jsonify({"msg": f"Area with ID {areaid} "
                                                             f"successfully deleted."})), 204
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@area.route('/api/getareabyprojectid/', methods=['POST'])
def getareabyprojectid():
    """
        ---
        post:
          description: Fetch areas by project id.
          parameters:
            -
              name: Authorization
              in: header
              type: string
              required: true
          requestBody:
            required: true
            content:
                application/json:
                    schema: InputSchema
          responses:
            '200':
              description: call successful
              content:
                application/json:
                  schema: OutputSchema
          tags:
              - fetchareabyprojectid
    """
    try:
        results = []
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "POST":
                    res = request.get_json(force=True)
                    projid = res['ProjectID']
                    data = Area.query.filter_by(projectid=projid).all()
                    if data is None:
                        return make_response(jsonify({"message": "No Areas present in the selected Project!!"})), 404
                    else:
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'projectid': d.projectid},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        return make_response(jsonify({"data": results})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
