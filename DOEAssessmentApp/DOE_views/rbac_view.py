from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import db
from DOEAssessmentApp.DOE_models.rbac_model import Role, Rbac
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail

rbac = Blueprint('rbac', __name__)

colsrole = ['id', 'name', 'companyid', 'creationdatetime', 'createdby']

colsusermanagement = ['id', 'empid', 'empname', 'emprole', 'empemail', 'emppasswordhash', 'companyid',
                      'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@rbac.route('/api/role', methods=['GET', 'POST'])
def rolemaster():
    """
        ---
        get:
          description: Fetch role(s).
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
              - getcreaterole
        post:
          description: Create a role.
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
              - getcreaterole
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
                    data = Role.query.all()
                    result = [{col: getattr(d, col) for col in colsrole} for d in data]
                    return make_response(jsonify({"data": result})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    companyid = res['companyid']
                    role = res['name']
                    existing_role = Role.query.filter(Role.name == role, Role.companyid == companyid).one_or_none()
                    if existing_role is None:
                        roleins = Role(role, companyid, session['empid'])
                        db.session.add(roleins)
                        db.session.commit()
                        data = Role.query.filter_by(id=roleins.id)
                        result = [{col: getattr(d, col) for col in colsrole} for d in data]
                        # region call audit trail method
                        auditins = Audittrail("ROLE", "ADD", None, str(result[0]), session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"message": f"Role {role} successfully inserted.",
                                                      "data": result[0]})), 201
                    else:
                        return make_response(jsonify({"message": f"Role {role} already exists."})), 400
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@rbac.route('/api/updelrole/', methods=['DELETE'])
def updelrolemaster():
    """
        ---
        delete:
          description: Delete a role.
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
              - deleterole
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
                roleid = res['roleid']
                data = Role.query.filter_by(id=roleid)
                result = [{col: getattr(d, col) for col in colsrole} for d in data]
                roledatabefore = result[0]
                result.clear()
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect ID"})), 404
                else:
                    if request.method == 'DELETE':
                        allrbacdata = Rbac.query.all()
                        for d in allrbacdata:
                            rbacdata = Rbac.query.filter_by(id=d.id)
                            for rd in rbacdata:
                                json_data = mergedict({'id': rd.id},
                                                      {'feature': rd.feature},
                                                      {'order': rd.order},
                                                      {'url': rd.url},
                                                      {'icon': rd.icon},
                                                      {'button': rd.button},
                                                      {'roles': str(rd.roles).split(",") if "," in rd.roles else [
                                                          rd.roles]},
                                                      {'creationdatetime': rd.creationdatetime},
                                                      {'updationdatetime': rd.updationdatetime},
                                                      {'modifiedby': rd.modifiedby})
                                result.append(json_data)
                            rbacdatabefore = result[0]
                            result.clear()
                            if data.first().name != rbacdata.first().roles:
                                if data.first().name in str(rbacdata.first().roles).split(','):
                                    rbacdata.first().roles = ','.join(
                                        [s for s in str(rbacdata.first().roles).split(',') if s != data.first().name])
                                    rbacdata.first().modifiedby = session['empid']
                                    db.session.add(rbacdata.first())
                                    db.session.commit()
                                    rbacdata = Rbac.query.filter_by(id=d.id)
                                    for rd in rbacdata:
                                        json_data = mergedict({'id': rd.id},
                                                              {'feature': rd.feature},
                                                              {'order': rd.order},
                                                              {'url': rd.url},
                                                              {'icon': rd.icon},
                                                              {'button': rd.button},
                                                              {'roles': str(rd.roles).split(
                                                                  ",") if "," in rd.roles else [
                                                                  rd.roles]},
                                                              {'creationdatetime': rd.creationdatetime},
                                                              {'updationdatetime': rd.updationdatetime},
                                                              {'modifiedby': rd.modifiedby})
                                        result.append(json_data)
                                    rbacdataafter = result[0]
                                    result.clear()
                                    # region call audit trail method
                                    auditins = Audittrail("RBAC", "UPDATE", str(rbacdatabefore), str(rbacdataafter),
                                                          session['empid'])
                                    db.session.add(auditins)
                                    db.session.commit()
                                    # end region
                                else:
                                    pass
                            else:
                                db.session.delete(rbacdata.first())
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("RBAC", "DELETE", str(rbacdatabefore), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                        userdata = Companyuserdetails.query.filter_by(emprole=data.first().name)
                        for u in userdata:
                            data = Companyuserdetails.query.filter_by(id=u.id)
                            result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                            userdatabefore = result[0]
                            result.clear()
                            u.emprole = 'no role'
                            u.modifiedby = session['empid']
                            db.session.add(u)
                            db.session.commit()
                            data = Companyuserdetails.query.filter_by(id=u.id)
                            result = [{col: getattr(d, col) for col in colsusermanagement} for d in data]
                            userdataafter = result[0]
                            result.clear()
                            # region call audit trail method
                            auditins = Audittrail("USER MANAGEMENT", "UPDATE", str(userdatabefore),
                                                  str(userdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("ROLE", "DELETE", str(roledatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"message": f"Role with ID {roleid} "
                                                                 f"successfully deleted."})), 204
            else:
                return make_response(({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@rbac.route('/api/rbac', methods=['GET', 'POST'])
def rolebasedaccesscontrol():
    """
        ---
        get:
          description: Fetch RBAC(s).
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
              - getcreaterbac
        post:
          description: Create a RBAC.
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
              - getcreaterbac
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
                    data = Rbac.query.all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'feature': d.feature},
                                              {'order': d.order},
                                              {'url': d.url},
                                              {'icon': d.icon},
                                              {'button': d.button},
                                              {'roles': str(d.roles).split(",") if "," in d.roles else [d.roles]},
                                              {'creationdatetime': d.creationdatetime},
                                              {'updationdatetime': d.updationdatetime},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
                elif request.method == "POST":
                    # this method can only be consumed by postman or curl and not browser
                    # hence no require of audit trail
                    res = request.get_json(force=True)
                    feat = res['feature']
                    existing_feature = Rbac.query.filter(Rbac.feature == feat).one_or_none()
                    if existing_feature is None:
                        featins = Rbac(feat, res['order'], res['url'], res['icon'], res['button'], res['roles'])
                        db.session.add(featins)
                        db.session.commit()
                        data = Rbac.query.filter_by(id=featins.id)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'feature': d.feature},
                                                  {'order': d.order},
                                                  {'url': d.url},
                                                  {'icon': d.icon},
                                                  {'button': d.button},
                                                  {'roles': str(d.roles).split(",") if "," in d.roles else [d.roles]},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        return make_response(jsonify({"message": f"RBAC with Feature {feat} "
                                                                 f"successfully inserted.",
                                                      "data": results[0]})), 201
                    else:
                        return make_response(jsonify({"message": f"RBAC with Feature {feat} already exists."})), 400
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@rbac.route('/api/updelrbac/', methods=['POST', 'PUT'])
def updelrolebasedaccesscontrol():
    """
        ---
        post:
          description: Fetch a RBAC.
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
              - updatedeleterbac
        put:
          description: Update a RBAC.
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
              - updatedeleterbac
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
                rbacid = res['rbacid']
                data = Rbac.query.filter_by(id=rbacid)
                for rd in data:
                    json_data = mergedict({'id': rd.id},
                                          {'feature': rd.feature},
                                          {'order': rd.order},
                                          {'url': rd.url},
                                          {'icon': rd.icon},
                                          {'button': rd.button},
                                          {'roles': str(rd.roles).split(",") if "," in rd.roles else [
                                              rd.roles]},
                                          {'creationdatetime': rd.creationdatetime},
                                          {'updationdatetime': rd.updationdatetime},
                                          {'modifiedby': rd.modifiedby})
                    results.append(json_data)
                rbacdatabefore = results[0]
                results.clear()
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect ID"})), 404
                else:
                    if request.method == 'POST':
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'feature': d.feature},
                                                  {'order': d.order},
                                                  {'url': d.url},
                                                  {'icon': d.icon},
                                                  {'button': d.button},
                                                  {'roles': str(d.roles).split(",") if "," in d.roles else [d.roles]},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        return make_response(jsonify({"data": results[0]})), 200
                    elif request.method == 'PUT':
                        # data.first().url = res['url']
                        # data.first().icon = res['icon']
                        # data.first().button = res['button']
                        # data.first().order = res['order']
                        data.first().roles = res['Roles']
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()
                        data = Rbac.query.filter_by(id=rbacid)
                        for rd in data:
                            json_data = mergedict({'id': rd.id},
                                                  {'feature': rd.feature},
                                                  {'order': rd.order},
                                                  {'url': rd.url},
                                                  {'icon': rd.icon},
                                                  {'button': rd.button},
                                                  {'roles': str(rd.roles).split(",") if "," in rd.roles else [
                                                      rd.roles]},
                                                  {'creationdatetime': rd.creationdatetime},
                                                  {'updationdatetime': rd.updationdatetime},
                                                  {'modifiedby': rd.modifiedby})
                            results.append(json_data)
                        rbacdataafter = results[0]
                        # region call audit trail method
                        auditins = Audittrail("RBAC", "UPDATE", str(rbacdatabefore), str(rbacdataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"message": f"RBAC with Feature {data.first().feature} "
                                                                 f"successfully updated."})), 200
            else:
                return make_response(({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@rbac.route('/api/fetchfeaturesbyrole/', methods=['POST'])
def fetchfeaturesbyrole():
    """
        ---
        post:
          description: Fetch features by role.
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
              - fetchfeaturesbyrole
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
                result = []
                role = res['role']
                if request.method == 'POST':
                    allrbacdata = Rbac.query.order_by(Rbac.order).all()
                    for d in allrbacdata:
                        rbacdata = Rbac.query.filter_by(id=d.id).first()
                        if role in rbacdata.roles:
                            result.append({"feature": rbacdata.feature, "order": rbacdata.order,
                                           "url": rbacdata.url, "icon": rbacdata.icon, "button": rbacdata.button})
                        else:
                            pass
                    return make_response(jsonify({"data": result})), 200
            else:
                return make_response(({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
