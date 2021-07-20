from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.project_model import Project
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.smtp_integration import trigger_mail

assigningprojectmanager = Blueprint('assigningprojectmanager', __name__)


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@assigningprojectmanager.route('/api/assigningprojectmanager', methods=['GET', 'POST'])
def getandpost():
    """
        ---
        get:
          description: Fetch project manager(s) assigned to project(s).
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
              - getcreateprojectmanagerassignment
        post:
          description: Assign a project to a project manager.
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
              - getcreateprojectmanagerassignment
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
                    data = Projectassignmenttomanager.query.all()
                    for user in data:
                        userdata = Companyuserdetails.query.filter_by(empid=user.emp_id)
                        data_proj = Project.query.filter_by(id=user.project_id)
                        if userdata.first() is not None and data_proj.first() is not None:
                            json_data = {'id': user.id, 'emp_id': user.emp_id, 'emp_name': userdata.first().empname,
                                         'project_id': user.project_id, 'project_name': data_proj.first().name,
                                         'status': user.status, 'creationdatetime': user.creationdatetime,
                                         'updationdatetime': user.updationdatetime}
                            results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    pm_id = res['emp_id']
                    pm_project_id = res['project_id']
                    existing_projectmanager = Projectassignmenttomanager.query.\
                        filter(Projectassignmenttomanager.emp_id == pm_id,
                               Projectassignmenttomanager. project_id == pm_project_id).one_or_none()
                    userdata = Companyuserdetails.query.filter_by(empid=pm_id).first()
                    empname = userdata.empname
                    companyid = userdata.companyid
                    mailto = userdata.empemail
                    project_details = Project.query.filter_by(id=pm_project_id).first()
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
                    if existing_projectmanager is None:
                        project_managers_in = Projectassignmenttomanager(pm_id, pm_project_id, session['empid'])
                        db.session.add(project_managers_in)
                        db.session.commit()

                        notification_data = Notification.query.filter_by(
                            event_name="PROJECTASSIGNMENT").first()
                        mail_subject = notification_data.mail_subject
                        mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                            projectname=project_details.name)
                        mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region

                        data = Projectassignmenttomanager.query.filter_by(id=project_managers_in.id).first()
                        userdata = Companyuserdetails.query.filter_by(empid=data.emp_id).first()
                        data_proj = Project.query.filter_by(id=data.project_id).first()
                        result = {'id': data.id, 'emp_id': data.emp_id, 'emp_name': userdata.empname,
                                  'project_id': data.project_id, 'project_name': data_proj.name,
                                  'status': data.status, 'creationdatetime': data.creationdatetime,
                                  'updationdatetime': data.updationdatetime}
                        data = Projectassignmenttomanager.query.filter_by(id=project_managers_in.id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'emp_id': d.emp_id},
                                                  {'project_id': d.project_id},
                                                  {'status': d.status},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        # region call audit trail method
                        auditins = Audittrail("PROJECT MANAGER ASSIGNMENT", "ADD", None, str(results[0]),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": "project manager successfully assigned.",
                                                      "data": result})), 201
                    else:
                        return make_response(jsonify({"msg": "project manager was already assigned before."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningprojectmanager.route('/api/associateprojectmanager/', methods=['PUT'])
def updateanddelete():
    """
        ---
        put:
          description: Associate/Disassociate a project manager.
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
              - associateprojectmanager
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
                data = Projectassignmenttomanager.query.filter_by(id=row_id)
                project_details = Project.query.filter_by(id=data.first().project_id)
                for d in data:
                    json_data = mergedict({'id': d.id},
                                          {'emp_id': d.emp_id},
                                          {'project_id': d.project_id},
                                          {'status': d.status},
                                          {'creationdatetime': d.creationdatetime},
                                          {'updationdatetime': d.updationdatetime},
                                          {'createdby': d.createdby},
                                          {'modifiedby': d.modifiedby})
                    results.append(json_data)
                projectassignmenttomanagerdatabefore = results[0]
                results.clear()
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect ID"})), 404
                else:
                    if request.method == 'PUT':
                        associate_status = res['associate_status']
                        if associate_status == 1:
                            data.first().status = 1
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()
                            if data.first() is not None:
                                userdata = Companyuserdetails.query.filter_by(empid=data.first().emp_id).first()
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
                                    event_name="PROJECTASSOCIATION").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                    status="associated",
                                                                                    projectname=project_details.first()
                                                                                    .name)
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region

                            data = Projectassignmenttomanager.query.filter_by(id=row_id)
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'emp_id': d.emp_id},
                                                      {'project_id': d.project_id},
                                                      {'status': d.status},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                results.append(json_data)
                            projectassignmenttomanagerdataafter = results[0]
                            # region call audit trail method
                            auditins = Audittrail("PROJECT MANAGER ASSIGNMENT", "UPDATE",
                                                  str(projectassignmenttomanagerdatabefore),
                                                  str(projectassignmenttomanagerdataafter), session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            return make_response(jsonify({"msg": "project manager associated successfully "})), 200
                        else:
                            data.first().status = 0
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()
                            if data.first() is not None:
                                userdata = Companyuserdetails.query.filter_by(empid=data.first().emp_id).first()
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
                                    event_name="PROJECTASSOCIATION").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                    status="disassociated",
                                                                                    projectname=project_details.first()
                                                                                    .name)
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region

                            data = Projectassignmenttomanager.query.filter_by(id=row_id)
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'emp_id': d.emp_id},
                                                      {'project_id': d.project_id},
                                                      {'status': d.status},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                results.append(json_data)
                            projectassignmenttomanagerdataafter = results[0]
                            # region call audit trail method
                            auditins = Audittrail("PROJECT MANAGER ASSIGNMENT", "UPDATE",
                                                  str(projectassignmenttomanagerdatabefore),
                                                  str(projectassignmenttomanagerdataafter), session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            return make_response(jsonify({"msg": "project manager disassociated successfully"})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningprojectmanager.route('/api/fetchprojectsassignedtomanager/', methods=['POST'])
def fetchprojectsassignedtomanager():
    try:
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
                    empid = res['emp_id']
                    data = Projectassignmenttomanager.query.filter_by(emp_id=empid)
                    for d in data:
                        data_proj = Project.query.filter_by(id=d.project_id)
                        if data_proj.first() is not None:
                            json_data = {'id': d.project_id, 'name': data_proj.first().name,
                                         'status': d.status, 'creationdatetime': d.creationdatetime,
                                         'updationdatetime': d.updationdatetime}
                            results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
