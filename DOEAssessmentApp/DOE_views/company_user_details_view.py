import publicip
from flask import *
from DOEAssessmentApp import app, db, COOKIE_TIME_OUT
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails, BlacklistToken
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail
from werkzeug.security import check_password_hash, generate_password_hash

companyuserdetails = Blueprint('companyuserdetails', __name__)

colsusermanagement = ['id', 'empid', 'empname', 'emprole', 'empemail', 'emppasswordhash', 'companyid',
                      'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


@companyuserdetails.route('/api/login', methods=['POST'])
def login():
    """
        ---
        post:
          description: Login
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
              - login
    """
    try:
        if request.method == "POST":
            res = request.get_json(force=True)
            if 'Email' in request.cookies:
                username = request.cookies.get('Email')
                password = request.cookies.get('Password')
                compuserdet = Companyuserdetails.query.filter_by(empemail=username).first()
                if compuserdet:
                    if check_password_hash(compuserdet.emppasswordhash, password):
                        token = compuserdet.encode_auth_token(res['Email'])
                        # session.permanent = True
                        session['empid'] = compuserdet.empid
                        resp = make_response(jsonify({'token': token.decode(), 'type': compuserdet.emprole,
                                                      'emp_id': compuserdet.empid,
                                                      'companyid': compuserdet.companyid,
                                                      'emp_name': compuserdet.empname}))
                        return resp, 200
                else:
                    return make_response(jsonify({"message": "Incorrect credentials !!"})), 401
            elif res and 'Email' in res and 'Password' in res:
                compuserdet = Companyuserdetails.query.filter_by(empemail=res['Email']).first()
                if compuserdet:
                    if check_password_hash(compuserdet.emppasswordhash, res['Password']):
                        token = compuserdet.encode_auth_token(res['Email'])
                        # session.permanent = True
                        session['empid'] = compuserdet.empid
                        if 'rememberme' in res:
                            rememberme = res['rememberme']
                            if rememberme is True:
                                resp = make_response(jsonify({'token': token.decode(), 'type': compuserdet.emprole,
                                                       'emp_id': compuserdet.empid,
                                                       'companyid': compuserdet.companyid,
                                                       'emp_name': compuserdet.empname}))
                                resp.set_cookie('Email', res['Email'], max_age=COOKIE_TIME_OUT)
                                resp.set_cookie('Password', res['Password'], max_age=COOKIE_TIME_OUT)
                                resp.set_cookie('Remember', 'checked', max_age=COOKIE_TIME_OUT)
                                return resp, 200
                            else:
                                session.permanent = True
                                return make_response(jsonify({'token': token.decode(), 'type': compuserdet.emprole,
                                                              'emp_id': compuserdet.empid,
                                                              'companyid': compuserdet.companyid,
                                                              'emp_name': compuserdet.empname})), 200
                        else:
                            session.permanent = True
                            return make_response(jsonify({'token': token.decode(), 'type': compuserdet.emprole,
                                                              'emp_id': compuserdet.empid,
                                                              'companyid': compuserdet.companyid,
                                                              'emp_name': compuserdet.empname})), 200
                    else:
                        return make_response(jsonify({"message": "Incorrect credentials !!"})), 401
                else:
                    return make_response(jsonify({"message": "User does not exist !!"})), 404
            else:
                return make_response(jsonify({"message": "Please provide email and password to login."})), 400
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@companyuserdetails.route('/api/logout', methods=['POST'])
def logout():
    """
        ---
        post:
          description: Logout
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
              - login
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
                    session.pop('empid', None)
                    # mark the token as blacklisted
                    blacklist_token = BlacklistToken(token=auth_token)
                    # insert the token
                    db.session.add(blacklist_token)
                    db.session.commit()
                    return make_response(jsonify({"message": "Successfully logged out."})), 200
            else:
                return make_response(({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 403
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@companyuserdetails.route('/api/forgotpassword', methods=['POST', 'PUT'])
def forgotpassword():
    try:
        res = request.get_json(force=True)
        if res and 'Email' in res:
            data = Companyuserdetails.query.filter_by(empemail=res['Email'])
            if data.first() is not None:
                empname = data.first().empname
                empid = data.first().empid
                companyid = data.first().companyid
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
                if 'pwd' in res:
                    if request.method == "PUT":
                        result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                        userdatabefore = result[0]
                        result.clear()
                        res = request.get_json(force=True)
                        pwd = res['pwd']
                        if check_password_hash(data.first().emppasswordhash, pwd):
                            return make_response(jsonify({"message": "Please type a new password !!"})), 400
                        else:
                            data.first().emppasswordhash = generate_password_hash(pwd)
                            data.first().modifiedby = empid
                            db.session.add(data.first())
                            db.session.commit()
                            data = Companyuserdetails.query.filter_by(empid=empid)
                            result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                            userdataafter = result[0]
                            # region call audit trail method
                            auditins = Audittrail("USER MANAGEMENT", "UPDATE", str(userdatabefore),
                                                  str(userdataafter),
                                                  empid)
                            db.session.add(auditins)
                            db.session.commit()
                            # end region

                            # region mail notification
                            notification_data = Notification.query.filter_by(
                                event_name="CHANGEPASSWORD").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname)
                            mailout = trigger_mail(mailfrom, res['Email'], host, epwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                            return make_response(jsonify({"msg": "Password reset successfully."})), 200
                else:
                    if request.method == "POST":
                        # region mail notification
                        notification_data = Notification.query.filter_by(
                            event_name="FORGOTPASSWORD").first()
                        mail_subject = notification_data.mail_subject
                        pubip = publicip.get()
                        url = "http://"+pubip+"/reset-password?email="+str(res['Email'])
                        mail_body = str(notification_data.mail_body).format(empname=empname, url=url)
                        mailout = trigger_mail(mailfrom, res['Email'], host, epwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region
                        return make_response(jsonify({"msg": "Please check your email to reset password."})), 200
            else:
                return make_response(jsonify({"msg": "Incorrect Email !!"})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
