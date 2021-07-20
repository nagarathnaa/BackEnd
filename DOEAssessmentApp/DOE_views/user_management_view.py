from flask import Blueprint, session, request, jsonify, make_response
from sqlalchemy import or_
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.company_details_model import Companydetails
from werkzeug.security import generate_password_hash, check_password_hash
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

user_management_view = Blueprint('user_management_view', __name__)

colsusermanagement = ['id', 'empid', 'empname', 'emprole', 'empemail', 'emppasswordhash', 'companyid',
                      'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


@user_management_view.route('/api/usermanagement', methods=['GET', 'POST'])
def getandpost():
    """
        ---
        get:
          description: Fetch user(s) details.
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
              - getcreateuser
        post:
          description: Create an user.
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
              - getcreateuser
    """
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "GET":
                    data = Companyuserdetails.query.all()
                    result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                    return make_response(jsonify({"data": result})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    user_empid = res['empid']
                    user_name = res['empname']
                    user_role = res['emprole']
                    user_email = res['empemail']
                    user_companyid = res['companyid']

                    existing_user = Companyuserdetails.query.filter(or_(Companyuserdetails.empid == user_empid,
                                                                        Companyuserdetails.empemail == user_email)). \
                        one_or_none()
                    company_details = Companydetails.query.filter(Companydetails.id == user_companyid).first()
                    emailconf = Emailconfiguration.query.filter_by(companyid=user_companyid).first()
                    if emailconf.email == 'default' and emailconf.host == 'default' \
                            and emailconf.password == 'default':
                        mailfrom = app.config.get('FROM_EMAIL')
                        host = app.config.get('HOST')
                        pwd = app.config.get('PWD')
                    else:
                        mailfrom = emailconf.email
                        host = emailconf.host
                        pwd = emailconf.password
                    if existing_user is None:
                        usermanagement = Companyuserdetails(user_empid, user_name, user_role, user_email,
                                                            generate_password_hash(res['EmployeePassword']),
                                                            user_companyid, session['empid'])
                        db.session.add(usermanagement)
                        db.session.commit()

                        # region mail notification
                        notification_data = Notification.query.filter_by(
                            event_name="ADDUSER").first()
                        companyname = company_details.companyname
                        mail_subject = str(notification_data.mail_subject).format(companyname=companyname)
                        mail_body = str(notification_data.mail_body).format(empname=user_name,
                                                                            companyname=companyname)
                        mailout = trigger_mail(mailfrom, user_email, host, pwd, mail_subject, user_name, mail_body)
                        print("======", mailout)
                        # end region

                        data = Companyuserdetails.query.filter_by(id=usermanagement.id)
                        result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                        # region call audit trail method
                        auditins = Audittrail("USER MANAGEMENT", "ADD", None, str(result[0]), session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": f"User {user_name} has been successfully added.",
                                                      "data": result[0]})), 201
                    else:
                        return make_response(jsonify({"msg": f"Please enter a different"
                                                             f" Employee Id or E-Mail for user {user_name}"
                                                             f" because it already exists."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@user_management_view.route('/api/updelusermanagement/', methods=['POST', 'PUT', 'DELETE'])
def updateanddelete():
    """
        ---
        post:
          description: Fetch an user.
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
              - updatedeleteuser
        put:
          description: Update an user.
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
              - updatedeleteuser
        delete:
          description: Delete an user.
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
              - updatedeleteuser
    """
    try:
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
                data = Companyuserdetails.query.filter_by(id=row_id)

                result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                userdatabefore = result[0]
                result.clear()
                if data.first() is None:
                    return make_response(jsonify({"msg": "Incorrect ID"})), 404
                else:
                    if request.method == 'POST':
                        result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                        return make_response(jsonify({"data": result[0]})), 200
                    elif request.method == 'PUT':
                        res = request.get_json(force=True)
                        user_role = res['emprole']

                        if data.first().emprole == 'admin':
                            count_user_with_admin_role = Companyuserdetails.query.filter_by(emprole=user_role).count()
                            if count_user_with_admin_role > 1:
                                data.first().emprole = user_role
                                data.first().modifiedby = session['empid']
                                db.session.add(data.first())
                                db.session.commit()

                                empname = data.first().empname
                                companyid = data.first().companyid
                                mailto = data.first().empemail

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
                                    event_name="UPDATEUSER").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                    rolename=user_role)
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region

                                data = Companyuserdetails.query.filter_by(id=row_id)
                                result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                                userdataafter = result[0]
                                # region call audit trail method
                                auditins = Audittrail("USER MANAGEMENT", "UPDATE", str(userdatabefore),
                                                      str(userdataafter),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                return make_response(
                                    jsonify(
                                        {"msg": f"User successfully updated with role {user_role}."})), 200
                            else:
                                return make_response(
                                    jsonify({
                                        "msg": "Please assign a user to admin role before "
                                               "changing the current admin's role"})), 400
                        else:
                            data.first().emprole = user_role
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()
                            empname = data.first().empname
                            companyid = data.first().companyid
                            mailto = data.first().empemail

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
                                event_name="UPDATEUSER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                rolename=user_role)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                            data = Companyuserdetails.query.filter_by(id=row_id)
                            result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                            userdataafter = result[0]
                            # region call audit trail method
                            auditins = Audittrail("USER MANAGEMENT", "UPDATE", str(userdatabefore),
                                                  str(userdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region

                            return make_response(
                                jsonify(
                                    {"msg": f"User successfully updated with role {user_role}."})), 200
                    elif request.method == 'DELETE':
                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("USER MANAGEMENT", "DELETE", str(userdatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": f"User with ID {row_id} "
                                                             f"successfully deleted."})), 204
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@user_management_view.route('/api/fetchusersbyrole', methods=['POST'])
def fetchusersbyrole():
    """
        ---
        post:
          description: Fetch users by role.
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
              - fetchusersbyrole
    """
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
                    res = request.get_json(force=True)
                    user_role = res['emprole']
                    data = Companyuserdetails.query.filter_by(emprole=user_role)
                    if data.first() is not None:
                        result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                        return make_response(jsonify({"data": result})), 200
                    else:
                        return make_response(jsonify({"msg": f"No users present with {user_role} role."})), 404
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


@user_management_view.route('/api/fetchuserprofiledata', methods=['GET'])
def fetchuserprofiledata():
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
                    data = Companyuserdetails.query.filter_by(empid=session['empid'])
                    if data.first() is not None:
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'empid': d.empid},
                                                  {'empname': d.empname},
                                                  {'emprole': d.emprole},
                                                  {'empemail': d.empemail})
                            result.append(json_data)
                        return make_response(jsonify({"data": result})), 200
                    else:
                        return make_response(jsonify({"message": "User does not exist !!"})), 404
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@user_management_view.route('/api/changepassword', methods=['PUT'])
def changepassword():
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "PUT":
                    data = Companyuserdetails.query.filter_by(empid=session['empid'])
                    empname = data.first().empname
                    companyid = data.first().companyid
                    mailto = data.first().empemail
                    emailconf = Emailconfiguration.query.filter_by(companyid=companyid).first()
                    if emailconf.email == 'default' and emailconf.host == 'default' \
                            and emailconf.password == 'default':
                        mailfrom = app.config.get('FROM_EMAIL')
                        host = app.config.get('HOST')
                        epwd = app.config.get('PWD')
                    else:
                        mailfrom = emailconf.email
                        host = emailconf.host
                        epwd = emailconf.password
                    result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                    userdatabefore = result[0]
                    result.clear()
                    if data.first() is not None:
                        res = request.get_json(force=True)
                        pwd = res['pwd']
                        if check_password_hash(data.first().emppasswordhash, pwd):
                            return make_response(jsonify({"message": "Please type a new password !!"})), 400
                        else:
                            data.first().emppasswordhash = generate_password_hash(pwd)
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()
                            data = Companyuserdetails.query.filter_by(empid=session['empid'])
                            result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                            userdataafter = result[0]
                            # region call audit trail method
                            auditins = Audittrail("USER MANAGEMENT", "UPDATE", str(userdatabefore),
                                                  str(userdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            # region mail notification
                            notification_data = Notification.query.filter_by(
                                event_name="CHANGEPASSWORD").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname)
                            mailout = trigger_mail(mailfrom, mailto, host, epwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region

                            return make_response(jsonify({"msg": f"Password changed successfully for"
                                                                 f" {session['empid']}",
                                                          "data": result})), 200
                    else:
                        return make_response(jsonify({"msg": "User does not exist !!"})), 404
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
