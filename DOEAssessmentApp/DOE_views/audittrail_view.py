from flask import Blueprint, session, request, jsonify, make_response
from sqlalchemy import desc
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails

audittrail = Blueprint('audittrail', __name__)


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@audittrail.route('/api/viewaudittrail/', methods=['GET'])
def viewaudittrail():
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
                    data = Audittrail.query.order_by(desc(Audittrail.operationdatetime)).limit(50).all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'modulename': d.modulename},
                                              {'operation': d.operation},
                                              {'databefore': d.databefore},
                                              {'dataafter': d.dataafter},
                                              {'operationdatetime': d.operationdatetime},
                                              {'operatedby': d.operatedby})
                        results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
