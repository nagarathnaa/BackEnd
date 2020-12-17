from flask import *
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails

user_management_view = Blueprint('user_management_view', __name__)


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@user_management_view.route('/api/usermanagement', methods=['GET', 'POST'])
def getAndPost():
    try:
        if request.method == "GET":
            results = []
            data = Companyuserdetails.query.all()
            for user in data:
                json_data = mergedict({'empid': user.empid}, {'empname': user.empname}, {'emprole': user.emprole},
                                      {'empemail': user.empemail}, {'companyid': user.companyid},
                                      {'emppasswordhash': user.emppasswordhash})
                results.append(json_data)

            return make_response(jsonify(results)), 200
        elif request.method == "POST":
            res = request.get_json(force=True)
            user_name = res['empname']
            usermanagement = Companyuserdetails(res['empid'], res['empname'], res['emprole'], res['empemail'],
                                                res['emppasswordhash'], res['companyid'])
            db.session.add(usermanagement)
            db.session.commit()
            return make_response(
                jsonify({"msg": f"UserManagement {user_name} successfully inserted."})), 201

    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 401


@user_management_view.route('/api/updelusermanagement/', methods=['PUT', 'DELETE'])
def updateAndDelete():
    try:

        res = request.get_json(force=True)
        usermanagementid = res['usermanagementid']
        data = Companyuserdetails.query.filter_by(id=usermanagementid).first()
        if data is None:
            return jsonify({"message": "Incorrect ID"})
        else:
            if request.method == 'PUT':
                user_name = res['empname']
                user_emppasswordhash = res['emppasswordhash']
                data.emppasswordhash = user_emppasswordhash
                data.empname = user_name
                db.session.add(data)
                db.session.commit()
                return jsonify({"msg": f"usermanagment {user_name} successfully updated."})


            elif request.method == 'DELETE':
                db.session.delete(data)
                db.session.commit()
                return jsonify({"msg": f"Functionality with ID {usermanagementid} successfully deleted."})

    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 401
