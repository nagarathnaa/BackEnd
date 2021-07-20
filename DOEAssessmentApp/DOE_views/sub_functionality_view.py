from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

sub_functionality_view = Blueprint('sub_functionality_view', __name__)

colsquestion = ['id', 'name', 'answer_type', 'answers', 'maxscore', 'subfunc_id', 'func_id', 'area_id', 'proj_id',
                'combination', 'mandatory', 'islocked', 'isdependentquestion',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


@sub_functionality_view.route('/api/subfunctionality', methods=['GET', 'POST'])
def getandpost():
    """
        ---
        get:
          description: Fetch sub-functionality(es).
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
              - getcreatesubfunctionality
        post:
          description: Create a sub-functionality.
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
              - getcreatesubfunctionality
    """
    try:
        result = []
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "GET":
                    data = Subfunctionality.query.all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'retake_assessment_days': d.retake_assessment_days},
                                              {'func_id': d.func_id},
                                              {'area_id': d.area_id},
                                              {'proj_id': d.proj_id},
                                              {'assessmentcompletion': str(d.assessmentcompletion)},
                                              {'achievedpercentage': str(d.achievedpercentage)},
                                              {'achievedlevel': d.achievedlevel},
                                              {'creationdatetime': d.creationdatetime},
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        result.append(json_data)
                    return make_response(jsonify({"data": result})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    subfunc_name = res['name']
                    subfunc_desc = res['description']
                    subfunc_retake_assess = res['retake_assessment_days']
                    subfunc_func_id = res['func_id']
                    subfunc_area_id = res['area_id']
                    subfunc_pro_id = res['proj_id']
                    countofquesinfunc = Question.query.filter_by(proj_id=subfunc_pro_id, area_id=subfunc_area_id,
                                                                 func_id=subfunc_func_id).count()

                    if countofquesinfunc == 0:
                        existing_subfunctionality = Subfunctionality.query.\
                            filter(Subfunctionality.name == subfunc_name, Subfunctionality.func_id == subfunc_func_id).\
                            one_or_none()
                        if existing_subfunctionality is None:
                            subfuncins = Subfunctionality(subfunc_name, subfunc_desc, subfunc_retake_assess,
                                                          subfunc_func_id, subfunc_area_id, subfunc_pro_id,
                                                          session['empid'])
                            db.session.add(subfuncins)
                            db.session.commit()

                            projectmanager = Projectassignmenttomanager.query.filter_by(project_id=subfunc_pro_id)
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
                                    event_name="ADDSUBFUNCTIONALITYTOMANAGER").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                    subfuncname=subfunc_name)
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region

                            data = Subfunctionality.query.filter_by(id=subfuncins.id)
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'name': d.name},
                                                      {'description': d.description},
                                                      {'retake_assessment_days': d.retake_assessment_days},
                                                      {'func_id': d.func_id},
                                                      {'area_id': d.area_id},
                                                      {'proj_id': d.proj_id},
                                                      {'assessmentcompletion': str(d.assessmentcompletion)},
                                                      {'achievedpercentage': str(d.achievedpercentage)},
                                                      {'achievedlevel': d.achievedlevel},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                      {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                result.append(json_data)
                            # region call audit trail method
                            auditins = Audittrail("SUB-FUNCTIONALITY", "ADD", None, str(result[0]), session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            return make_response(jsonify({"msg": f"Subfunctionality {subfunc_name}  has "
                                                                 f"been successfully added.",
                                                          "data": result[0]})), 201
                        else:

                            data_func = Functionality.query.filter_by(id=subfunc_func_id).first()
                            return make_response(jsonify({"msg": f"Subfunctionality {subfunc_name} already exists "
                                                                 f"for functionality {data_func.name}."})), 400
                    else:
                        data_func = Functionality.query.filter_by(id=subfunc_func_id).first()
                        return make_response(jsonify({"msg": f"Can not add Subfunctionality under functionality"
                                                             f" {data_func.name} because it has questions."
                                                             f" Please add a new functionality and then add"
                                                             f" a subfunctionality under it."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@sub_functionality_view.route('/api/updelsubfunctionality/', methods=['POST', 'PUT', 'DELETE'])
def updateanddelete():
    """
        ---
        post:
          description: Fetch a sub-functionality.
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
              - updatedeletesubfunctionality
        put:
          description: Update a sub-functionality.
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
              - updatedeletesubfunctionality
        delete:
          description: Delete a sub-functionality.
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
              - updatedeletesubfunctionality
    """
    try:
        result = []
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                res = request.get_json(force=True)
                row_id = res['row_id']
                data = Subfunctionality.query.filter_by(id=row_id)

                for d in data:
                    json_data = mergedict({'id': d.id},
                                          {'name': d.name},
                                          {'description': d.description},
                                          {'retake_assessment_days': d.retake_assessment_days},
                                          {'func_id': d.func_id},
                                          {'area_id': d.area_id},
                                          {'proj_id': d.proj_id},
                                          {'assessmentcompletion': str(d.assessmentcompletion)},
                                          {'achievedpercentage': str(d.achievedpercentage)},
                                          {'achievedlevel': d.achievedlevel},
                                          {'creationdatetime': d.creationdatetime},
                                          {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                          {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                          {'updationdatetime': d.updationdatetime},
                                          {'createdby': d.createdby},
                                          {'modifiedby': d.modifiedby})
                    result.append(json_data)
                subfuncdatabefore = result[0]
                result.clear()
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect ID"})), 404
                else:
                    if request.method == 'POST':
                        return make_response(jsonify({"data": subfuncdatabefore})), 200
                    elif request.method == 'PUT':
                        subfunc_desc = res['description']
                        subfunc_retake_assess = res['retake_assessment_days']
                        data.first().description = subfunc_desc
                        data.first().retake_assessment_days = subfunc_retake_assess
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()

                        projectmanager = Projectassignmenttomanager.query.filter_by(
                            project_id=data.first().proj_id)
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
                                event_name="UPDATESUBFUNCTIONALITYTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                subfuncname=data.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                        data = Subfunctionality.query.filter_by(id=row_id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'retake_assessment_days': d.retake_assessment_days},
                                                  {'func_id': d.func_id},
                                                  {'area_id': d.area_id},
                                                  {'proj_id': d.proj_id},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            result.append(json_data)
                        subfuncdataafter = result[0]
                        # region call audit trail method
                        auditins = Audittrail("SUB-FUNCTIONALITY", "UPDATE", str(subfuncdatabefore),
                                              str(subfuncdataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": f"Subfunctionality {data.first().name} "
                                                             f"successfully updated."})), 200
                    elif request.method == 'DELETE':
                        projectmanager = Projectassignmenttomanager.query.filter_by(
                            project_id=data.first().proj_id)
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
                                event_name="DELETESUBFUNCTIONALITYTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                subfuncname=data.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("SUB-FUNCTIONALITY", "DELETE", str(subfuncdatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        data_question = Question.query.filter_by(subfunc_id=row_id)
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
                        return make_response(jsonify({"msg": f"Subfunctionality with ID {row_id} "
                                                             f"successfully deleted."})), 204
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@sub_functionality_view.route('/api/getsubfunctionalitybyfunctionalityid/', methods=['POST'])
def getsubfunctionalitybyfunctionalityid():
    """
        ---
        post:
          description: Fetch sub-functionalities by functionality id.
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
              - fetchsubfunctionalitiesbyfunctionalityid
    """
    try:
        subfuncexists = True
        datalist = []
        data = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "POST":
                    results = []
                    res = request.get_json(force=True)
                    if type(res['FunctionalityID']) is list:
                        funcid = res['FunctionalityID']
                        for f in funcid:
                            data = Subfunctionality.query.filter_by(func_id=f).all()
                            if data is not None:
                                datalist.append(data)
                    else:
                        funcid = res['FunctionalityID']
                        data = Subfunctionality.query.filter_by(func_id=funcid).all()
                        if data is None:
                            subfuncexists = False
                    if subfuncexists is False:
                        return make_response(jsonify({"msg": "No Subfunctionalities present in the "
                                                             "selected Functionality!!"})), 404
                    else:
                        if len(datalist) > 0:
                            for data in datalist:
                                for d in data:
                                    json_data = mergedict({'id': d.id},
                                                          {'name': d.name},
                                                          {'description': d.description},
                                                          {'retake_assessment_days': d.retake_assessment_days},
                                                          {'func_id': d.func_id},
                                                          {'area_id': d.area_id},
                                                          {'proj_id': d.proj_id},
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
                        else:
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'name': d.name},
                                                      {'description': d.description},
                                                      {'retake_assessment_days': d.retake_assessment_days},
                                                      {'func_id': d.func_id},
                                                      {'area_id': d.area_id},
                                                      {'proj_id': d.proj_id},
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
