import uuid
from flask import *
from DOEAssessmentApp import db
from DOEAssessmentApp.DOE_models.company_details_model import Companydetails

companydetails = Blueprint('companydetails', __name__)

colscompanydetails = ['id', 'companyname', 'registeredaddress', 'billingaddress', 'registrationkey',
                      'registrationkeyvalidated', 'creationdatetime', 'updationdatetime']


@companydetails.route('/api/companydetails', methods=['GET', 'POST'])
def companydetail():
    """
        ---
        get:
          description: Fetch all registered company details.
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
              - getcreatecompanydetails
        post:
          description: Register a company into the app.
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
              - getcreatecompanydetails
    """
    try:
        if request.method == "GET":
            data = Companydetails.query.all()
            for d in data:
                if d is not None:
                    result = [{col: getattr(d, col) for col in colscompanydetails} for d in data]
                    return make_response(jsonify({"data": result[0]})), 200
        elif request.method == "POST":
            res = request.get_json(force=True)
            cname = res['CompanyName']
            regadrs = res['RegisteredAddress']
            billadrs = res['BillingAddress']
            regkey = str(uuid.uuid4())
            existing_company = Companydetails.query.filter(Companydetails.companyname == cname).one_or_none()
            if existing_company is None:
                compdet = Companydetails(cname, regadrs, billadrs, regkey)
                db.session.add(compdet)
                db.session.commit()
                # send a mail to company admin with registration key which will be validated first time after install
                return make_response(jsonify({"msg": f"Company details with Company Name {cname} "
                                                     f"successfully inserted."})), 201
            else:
                return make_response(jsonify({"msg": f"Company details with Company Name {cname} "
                                                     f"already exists."})), 400
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@companydetails.route('/api/updatecompanydetails', methods=['POST', 'PUT'])
def updatecompanydetails():
    try:
        res = request.get_json(force=True)
        cmpny_id = res['id']
        data = Companydetails.query.filter_by(id=cmpny_id)
        if data.first() is None:
            return make_response(jsonify({"msg": "No company details found !!"})), 404
        else:
            if request.method == 'POST':
                result = [{col: getattr(d, col) for col in colscompanydetails} for d in data]
                return make_response(jsonify({"data": result[0]})), 200
            elif request.method == "PUT":
                cname = res['CompanyName']
                regadrs = res['RegisteredAddress']
                billadrs = res['BillingAddress']
                data.first().companyname = cname
                data.first().registeredaddress = regadrs
                data.first().billingaddress = billadrs
                db.session.add(data.first())
                db.session.commit()
                return make_response(jsonify({"msg": f"Company details with Company Name {cname} "
                                                     f"successfully updated."})), 201
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
