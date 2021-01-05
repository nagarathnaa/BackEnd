from flask import *
from DOEAssessmentApp import db
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails

emailconfig = Blueprint('emailconfig', __name__)

colsemailconf = ['id', 'email', 'host', 'password', 'companyid', 'creationdatetime',
                 'updationdatetime']


@emailconfig.route('/api/emailconfig', methods=['GET', 'POST'])
def emailconfigs():
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "GET":
                    data = Emailconfiguration.query.all()
                    result = [{col: getattr(d, col) for col in colsemailconf} for d in data]
                    return make_response(jsonify({"data": result})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    companyid = res['companyid']
                    if 'Email' in res and 'Host' in res and 'Password' in res:
                        emailid = res['Email']
                        host = res['Host']
                        password = res['Password']
                    else:
                        emailid = 'default'
                        host = 'default'
                        password = 'default'
                    companyemailconfcount = Emailconfiguration.query.filter_by(companyid=companyid).count()
                    if companyemailconfcount == 0:
                        emailconf = Emailconfiguration(emailid, host, password, companyid)
                        db.session.add(emailconf)
                        db.session.commit()
                        data = Emailconfiguration.query.filter_by(id=emailconf.id)
                        result = [{col: getattr(d, col) for col in colsemailconf} for d in data]
                        return make_response(jsonify({"message": f"Email Configuration successfully inserted "
                                                                 f"for your company",
                                                      "data": result[0]})), 201
                    else:
                        return make_response(jsonify({"message": f"Email Configuration already exists for "
                                                                 f"your company"})), 400
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@emailconfig.route('/api/updelemailconfig/', methods=['POST', 'PUT'])
def updelemailconfig():
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                res = request.get_json(force=True)
                companyid = res['companyid']
                data = Emailconfiguration.query.filter_by(companyid=companyid)
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect company"})), 404
                else:
                    if request.method == 'POST':
                        result = [{col: getattr(d, col) for col in colsemailconf} for d in data]
                        return make_response(jsonify({"data": result[0]})), 200
                    elif request.method == 'PUT':
                        if 'Email' in res and 'Host' in res and 'Password' in res:
                            data.first().email = res['Email']
                            data.first().host = res['Host']
                            data.first().password = res['Password']
                        else:
                            data.first().email = 'default'
                            data.first().host = 'default'
                            data.first().password = 'default'
                        db.session.add(data.first())
                        db.session.commit()
                        return make_response(jsonify({"message": f"Email Configuration successfully updated "
                                                                 f"for your company"})), 200
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
