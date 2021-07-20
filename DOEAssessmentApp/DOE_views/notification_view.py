from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import db
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.DOE_models.notification_received_model import NotificationReceived
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from sqlalchemy import desc

notific = Blueprint('notific', __name__)


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@notific.route('/api/viewnotification', methods=['GET', 'POST'])
def viewnotification():
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
                    data = Notification.query.all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'role': str(d.role).split(",") if "," in d.role else [d.role]},
                                              {'event_name': d.event_name},
                                              {'mail_subject': d.mail_subject},
                                              {'mail_body': d.mail_body},
                                              {'app_notif_body': d.app_notif_body},
                                              {'companyid': d.companyid},
                                              {'creationdatetime': d.creationdatetime},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    role = res['role']
                    event_name = res['event_name']
                    mail_subject = res['mail_subject']
                    mail_body = res['mail_body']
                    app_notif_body = res['app_notif_body'] if 'app_notif_body' in res else None
                    companyid = res['companyid']
                    notification_data = Notification.query.filter(Notification.event_name == event_name).one_or_none()
                    if notification_data is None:
                        notifications = Notification(role, event_name, mail_subject, mail_body,
                                                     app_notif_body, companyid,
                                                     session['empid'])
                        db.session.add(notifications)
                        db.session.commit()
                        data = Notification.query.filter_by(id=notifications.id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'role': str(d.role).split(",") if "," in d.role else [d.role]},
                                                  {'event_name': d.event_name},
                                                  {'mail_subject': d.mail_subject},
                                                  {'mail_body': d.mail_body},
                                                  {'app_notif_body': d.app_notif_body},
                                                  {'companyid': d.companyid},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        # region call audit trail method
                        auditins = Audittrail("NOTIFICATION", "ADD", None, str(results[0]), session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": "Notification data successfully inserted.",
                                                      "data": results[0]})), 201
                    else:
                        return make_response(jsonify({"msg": "Notification data already exists."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@notific.route('/api/updelnotification/', methods=['POST', 'PUT', 'DELETE'])
def updelnotification():
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
                notificationid = res['notificationid']
                data = Notification.query.filter_by(id=notificationid)
                for nd in data:
                    json_data = mergedict({'id': nd.id},
                                          {'role': str(nd.role).split(",") if "," in nd.role else [nd.role]},
                                          {'event_name': nd.event_name},
                                          {'mail_subject': nd.mail_subject},
                                          {'mail_body': nd.mail_body},
                                          {'app_notif_body': nd.app_notif_body},
                                          {'companyid': nd.companyid},
                                          {'creationdatetime': nd.creationdatetime},
                                          {'updationdatetime': nd.updationdatetime},
                                          {'createdby': nd.createdby},
                                          {'modifiedby': nd.modifiedby})
                    results.append(json_data)
                notificationdatabefore = results[0]
                results.clear()
                if data.first() is None:
                    return make_response(jsonify({"msg": "Incorrect ID"})), 404
                else:
                    if request.method == 'POST':
                        for nd in data:
                            json_data = mergedict({'id': nd.id},
                                                  {'role': str(nd.role).split(",") if "," in nd.role else [nd.role]},
                                                  {'event_name': nd.event_name},
                                                  {'mail_subject': nd.mail_subject},
                                                  {'mail_body': nd.mail_body},
                                                  {'app_notif_body': nd.app_notif_body},
                                                  {'companyid': nd.companyid},
                                                  {'creationdatetime': nd.creationdatetime},
                                                  {'updationdatetime': nd.updationdatetime},
                                                  {'createdby': nd.createdby},
                                                  {'modifiedby': nd.modifiedby})
                            results.append(json_data)
                        return make_response(jsonify({"data": results[0]})), 200
                    elif request.method == 'PUT':
                        data.first().mail_subject = res['mail_subject']
                        data.first().mail_body = res['mail_body']
                        data.first().app_notif_body = res['app_notif_body'] if 'app_notif_body' in res else None
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()
                        data = Notification.query.filter_by(id=notificationid)
                        for nd in data:
                            json_data = mergedict({'id': nd.id},
                                                  {'role': str(nd.role).split(",") if "," in nd.role else [nd.role]},
                                                  {'event_name': nd.event_name},
                                                  {'mail_subject': nd.mail_subject},
                                                  {'mail_body': nd.mail_body},
                                                  {'app_notif_body': nd.app_notif_body},
                                                  {'companyid': nd.companyid},
                                                  {'creationdatetime': nd.creationdatetime},
                                                  {'updationdatetime': nd.updationdatetime},
                                                  {'createdby': nd.createdby},
                                                  {'modifiedby': nd.modifiedby})
                            results.append(json_data)
                        notificationdataafter = results[0]
                        # region call audit trail method
                        auditins = Audittrail("NOTIFICATION", "UPDATE", str(notificationdatabefore),
                                              str(notificationdataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"msg": "NOTIFICATION with Features "
                                                             "successfully updated."})), 200
                    elif request.method == 'DELETE':
                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("NOTIFICATION", "DELETE", str(notificationdatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        return make_response(jsonify({"msg": f"NOTIFICATION with ID {notificationid} "
                                                             f"successfully deleted."})), 204
            else:
                return make_response(({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@notific.route('/api/fetchnotification', methods=['GET', 'PUT'])
def fetchnotification():
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
                data = NotificationReceived.query.filter_by(empid=session['empid']).order_by(
                    desc(NotificationReceived.creationdatetime)).limit(50)
                if request.method == "GET":

                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'empid': d.empid},
                                              {'status': d.status},
                                              {'notification_content': d.notification_content},
                                              {'creationdatetime': d.creationdatetime},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    return make_response(jsonify({"data": results})), 200

                elif request.method == "PUT":
                    data = NotificationReceived.query.filter(NotificationReceived.empid == session['empid'],
                                                             NotificationReceived.status == 0)
                    for d in data:
                        eachadata = NotificationReceived.query.filter_by(id=d.id).first()
                        eachadata.status = 1
                        db.session.add(eachadata)
                        db.session.commit()
                    data = NotificationReceived.query.filter_by(empid=session['empid']).order_by(
                        desc(NotificationReceived.creationdatetime)).limit(50)
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'empid': d.empid},
                                              {'status': d.status},
                                              {'notification_content': d.notification_content},
                                              {'creationdatetime': d.creationdatetime},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    return make_response(jsonify({"msg": "Notifications are seen", "data": results})), 200

            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
