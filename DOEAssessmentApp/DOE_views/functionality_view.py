from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.area_model import Area
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

functionality_view = Blueprint('functionality_view', __name__)

cols_subfunc = ['id', 'name', 'description', 'retake_assessment_days', 'func_id', 'area_id', 'proj_id',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']

colsquestion = ['id', 'name', 'answer_type', 'answers', 'maxscore', 'subfunc_id', 'func_id', 'area_id', 'proj_id',
                'combination', 'mandatory', 'islocked', 'isdependentquestion',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


@functionality_view.route('/api/functionality', methods=['GET', 'POST'])
def getandpost():
    """
        ---
        get:
          description: Fetch functionality(es).
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
              - getcreatefunctionality
        post:
          description: Create a functionality.
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
              - getcreatefunctionality
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
                    data = Functionality.query.all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'priority': d.priority},
                                              {'retake_assessment_days': d.retake_assessment_days},
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
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    func_name = res['name']
                    func_desc = res['description']
                    priority = res['priority']
                    func_retake_assess = res['retake_assessment_days']
                    func_area_id = res['area_id']
                    func_pro_id = res['proj_id']
                    projectmanager = Projectassignmenttomanager.query.filter_by(project_id=func_pro_id)
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
                            event_name="ADDFUNCTIONALITYTOMANAGER").first()
                        mail_subject = notification_data.mail_subject
                        mail_body = str(notification_data.mail_body).format(empname=empname, fname=func_name)
                        mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region

                    existing_functionality = Functionality.query.filter(Functionality.name == func_name,
                                                                        Functionality.area_id == func_area_id).\
                        one_or_none()
                    if existing_functionality is None:
                        funcins = Functionality(func_name, func_desc, func_retake_assess, func_area_id, func_pro_id,
                                                session['empid'], priority)
                        db.session.add(funcins)
                        db.session.commit()

                        data = Functionality.query.filter_by(id=funcins.id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'retake_assessment_days': d.retake_assessment_days},
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
                        # region call audit trail method
                        auditins = Audittrail("FUNCTIONALITY", "ADD", None, str(results[0]), session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region

                        return make_response(jsonify({"msg": f"Functionality {func_name}  has been successfully added.",
                                                      "data": results[0]})), 201
                    else:
                        data_area = Area.query.filter_by(id=func_area_id).first()
                        return make_response(jsonify({"msg": f"Functionality {func_name} already "
                                                             f"exists for area {data_area.name}."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@functionality_view.route('/api/updelfunctionality/', methods=['POST', 'PUT', 'DELETE'])
def updateanddelete():
    """
        ---
        post:
          description: Fetch a functionality.
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
              - updatedeletefunctionality
        put:
          description: Update a functionality.
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
              - updatedeletefunctionality
        delete:
          description: Delete a functionality.
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
              - updatedeletefunctionality
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
                row_id = res['row_id']
                data = Functionality.query.filter_by(id=row_id)

                for d in data:
                    json_data = mergedict({'id': d.id},
                                          {'name': d.name},
                                          {'description': d.description},
                                          {'priority': d.priority},
                                          {'retake_assessment_days': d.retake_assessment_days},
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
                funcdatabefore = results[0]
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
                                                  {'retake_assessment_days': d.retake_assessment_days},
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
                        return make_response(jsonify({"data": results[0]})), 200
                    elif request.method == 'PUT':
                        func_desc = res['description']
                        priority = res['priority']
                        func_retake_assessment_days = res['retake_assessment_days']
                        data.first().description = func_desc
                        data.first().priority = priority
                        data.first().retake_assessment_days = func_retake_assessment_days
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()
                        data = Functionality.query.filter_by(id=row_id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'retake_assessment_days': d.retake_assessment_days},
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
                        funcdataafter = results[0]
                        # region call audit trail method
                        auditins = Audittrail("FUNCTIONALITY", "UPDATE", str(funcdatabefore), str(funcdataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        projectmanager = Projectassignmenttomanager.query.filter_by(project_id=data.first().proj_id)
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
                                event_name="UPDATEFUNCTIONALITYTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                fname=data.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region

                        return make_response(jsonify({"msg": f"Functionality {data.first().name} "
                                                             f"successfully updated."})), 200
                    elif request.method == 'DELETE':

                        projectmanager = Projectassignmenttomanager.query.filter_by(project_id=data.first().proj_id)
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
                                event_name="DELETEFUNCTIONALITYTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                fname=data.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                        db.session.delete(data.first())
                        db.session.commit()

                        # region call audit trail method
                        auditins = Audittrail("FUNCTIONALITY", "DELETE", str(funcdatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        data_subfunc = Subfunctionality.query.filter_by(func_id=row_id)
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
                        data_question = Question.query.filter_by(func_id=row_id)
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
                        return make_response(jsonify({"msg": f"Functionality with ID {row_id} "
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


@functionality_view.route('/api/getfunctionalitybyareaid/', methods=['POST'])
def getfunctionalitybyareaid():
    """
        ---
        post:
          description: Fetch functionalities by area id.
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
              - fetchfunctionalitiesbyareaid
    """
    try:
        funcexists = True
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
                    if type(res['AreaID']) is list:
                        areaid = res['AreaID']
                        for a in areaid:
                            data = Functionality.query.filter_by(area_id=a).all()
                            if data is not None:
                                datalist.append(data)
                    else:
                        areaid = res['AreaID']
                        data = Functionality.query.filter_by(area_id=areaid).all()
                        if data is None:
                            funcexists = False
                    if funcexists is False:
                        return make_response(jsonify({"msg": "No Functionalities present in the "
                                                             "selected Area!!"})), 404
                    else:
                        if len(datalist) > 0:
                            for data in datalist:
                                for d in data:
                                    json_data = mergedict({'id': d.id},
                                                          {'name': d.name},
                                                          {'description': d.description},
                                                          {'priority': d.priority},
                                                          {'retake_assessment_days': d.retake_assessment_days},
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
                                                      {'priority': d.priority},
                                                      {'retake_assessment_days': d.retake_assessment_days},
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
                        return make_response(jsonify(results)), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
