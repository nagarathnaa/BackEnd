from flask import Blueprint, session, request, make_response, jsonify
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

question = Blueprint('question', __name__)

colsquestion = ['id', 'name', 'answer_type', 'answers', 'maxscore', 'subfunc_id', 'func_id', 'area_id', 'proj_id',
                'combination', 'mandatory', 'islocked', 'isdependentquestion',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


@question.route('/api/question', methods=['GET', 'POST'])
def getaddquestion():
    """
        ---
        get:
          description: Fetch question(s).
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
              - getcreatequestion
        post:
          description: Create a question.
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
              - getcreatequestion
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
                    data = Question.query.all()
                    result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                    return make_response(jsonify({"data": result})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    quesname = res['QuestionName']
                    answertype = res['AnswerType']
                    answers = res['Answers']
                    maxscore = res["MaxScore"]
                    funcid = res['func_id']
                    areaid = res['area_id']
                    projid = res['proj_id']
                    mandatory = res['mandatory']
                    if "subfunc_id" in res:
                        subfuncid = res['subfunc_id']
                        combination = str(projid) + str(areaid) + str(funcid) + str(subfuncid) + str(quesname)
                    else:
                        subfuncid = None
                        combination = str(projid) + str(areaid) + str(funcid) + str(quesname)
                    existing_question = Question.query.filter(Question.combination == combination).one_or_none()

                    projectmanager = Projectassignmenttomanager.query.filter_by(project_id=projid)
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
                            event_name="ADDQUESTIONTOMANAGER").first()
                        mail_subject = notification_data.mail_subject
                        mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                            questionname=quesname)
                        mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region
                    if existing_question is None:
                        quesins = Question(quesname, answertype, answers, maxscore, subfuncid, funcid, areaid, projid,
                                           combination, mandatory, session['empid'])
                        db.session.add(quesins)
                        db.session.commit()

                        data = Question.query.filter_by(id=quesins.id)
                        result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                        # region call audit trail method
                        auditins = Audittrail("QUESTION", "ADD", None, str(result[0]), session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region

                        return make_response(jsonify({"msg": f"Question {quesname} successfully inserted.",
                                                      "data": result[0]})), 201
                    else:
                        if subfuncid:
                            data_sub = Subfunctionality.query.filter_by(id=subfuncid).first()
                            return make_response(
                                jsonify({"msg": f"Question {quesname} already exists for subfunctionality "
                                                f"{data_sub.name}."})), 400
                        elif funcid:
                            data_func = Functionality.query.filter_by(id=funcid).first()
                            return make_response(
                                jsonify({"msg": f"Question {quesname} already exists for functionality "
                                                f"{data_func.name}."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@question.route('/api/updelquestion', methods=['POST', 'PUT', 'DELETE'])
def updateanddelete():
    """
        ---
        post:
          description: Fetch a question.
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
              - updatedeletequestion
        put:
          description: Update a question.
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
              - updatedeletequestion
        delete:
          description: Delete a question.
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
              - updatedeletequestion
    """
    try:
        option = None
        parentid = None
        quesdatabefore = None
        quesexists = True
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
                res = request.get_json(force=True)
                if 'parentid' in res and 'option' in res:
                    parentid = res['parentid']
                    option = res['option']
                if type(res['questionid']) is list:
                    questionid = res['questionid']
                    for q in questionid:
                        data = Question.query.filter_by(id=q)
                        if data.first() is not None:
                            datalist.append(data)
                else:
                    questionid = res['questionid']
                    data = Question.query.filter_by(id=questionid)
                    result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                    quesdatabefore = result[0]
                    result.clear()
                    if data.first() is None:
                        quesexists = False
                if quesexists is False:
                    return make_response(jsonify({"msg": "Incorrect ID"})), 404
                else:
                    if request.method == "POST":
                        lists = []
                        if len(datalist) > 0:
                            for data in datalist:
                                for user in data:
                                    json_data = {'question_id': user.id, 'question_name': user.name,
                                                 'answer_type': user.answer_type, 'maxscore': user.maxscore,
                                                 'answers': user.answers, 'proj_id': user.proj_id,
                                                 'area_id': user.area_id,
                                                 'func_id': user.func_id, 'subfunc_id': user.subfunc_id,
                                                 'mandatory': user.mandatory,
                                                 'updationdatetime': user.updationdatetime,
                                                 'isdependentquestion': user.isdependentquestion}
                                    lists.append(json_data)
                        else:
                            for user in data:
                                json_data = {'question_id': user.id, 'question_name': user.name,
                                             'answer_type': user.answer_type, 'maxscore': user.maxscore,
                                             'answers': user.answers, 'proj_id': user.proj_id, 'area_id': user.area_id,
                                             'func_id': user.func_id, 'subfunc_id': user.subfunc_id,
                                             'mandatory': user.mandatory,
                                             'updationdatetime': user.updationdatetime,
                                             'isdependentquestion': user.isdependentquestion}
                                lists.append(json_data)
                        return make_response(jsonify({"data": lists})), 200
                    elif request.method == 'PUT':
                        quesname = res['QuestionName']
                        answertype = res['AnswerType']
                        answers = res['Answers']
                        maxscore = res["MaxScore"]
                        funcid = res['func_id']
                        areaid = res['area_id']
                        projid = res['proj_id']
                        mandatory = res['mandatory']
                        if "subfunc_id" in res:
                            subfuncid = res['subfunc_id']
                            combination = str(projid) + str(areaid) + str(funcid) + str(subfuncid) + str(quesname)
                        else:
                            subfuncid = None
                            combination = str(projid) + str(areaid) + str(funcid) + str(quesname)
                        existing_question = Question.query.filter(Question.combination == combination).one_or_none()

                        projectmanager = Projectassignmenttomanager.query.filter_by(
                            project_id=projid)
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
                                event_name="UPDATEQUESTIONTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                questionname=quesname)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region

                        if quesname != data.first().name:
                            if existing_question is None:
                                data.first().name = quesname
                                data.first().answer_type = answertype
                                data.first().answers = answers
                                data.first().maxscore = maxscore
                                data.first().mandatory = mandatory
                                data.first().islocked = 0
                                data.first().modifiedby = session['empid']
                                db.session.add(data.first())
                                db.session.commit()

                                data = Question.query.filter_by(id=questionid)
                                result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                quesdataafter = result[0]
                                # region call audit trail method
                                auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore),
                                                      str(quesdataafter),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                return make_response(jsonify({"msg": f"Question {quesname} successfully updated"})), 200
                            else:
                                if subfuncid:
                                    data_sub = Subfunctionality.query.filter_by(id=subfuncid).first()
                                    return make_response(
                                        jsonify({"msg": f"Question {quesname} already exists for subfunctionality "
                                                        f"{data_sub.name}."})), 400
                                elif funcid:
                                    data_func = Functionality.query.filter_by(id=funcid).first()
                                    return make_response(
                                        jsonify({"msg": f"Question {quesname} already exists for functionality "
                                                        f"{data_func.name}."})), 400
                        else:
                            data.first().answer_type = answertype
                            data.first().answers = answers
                            data.first().maxscore = maxscore
                            data.first().mandatory = mandatory
                            data.first().islocked = 0
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()
                            data = Question.query.filter_by(id=questionid)
                            result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                            quesdataafter = result[0]
                            # region call audit trail method
                            auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore),
                                                  str(quesdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            return make_response(jsonify({"msg": f"Question {quesname} successfully updated"})), 200
                    elif request.method == 'DELETE':

                        projectmanager = Projectassignmenttomanager.query.filter_by(
                            project_id=data.first().proj_id)
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
                                event_name="DELETEQUESTIONTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                questionname=data.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region

                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("QUESTION", "DELETE", str(quesdatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        if parentid is not None and option is not None:
                            parentdata = Question.query.filter_by(id=parentid)
                            result = [{col: getattr(d, col) for col in colsquestion} for d in parentdata]
                            parentquesdatabefore = result[0]
                            result.clear()
                            newanswers = parentdata.first().answers
                            for a in newanswers:
                                if option in a:
                                    if isinstance(a['childquestionid'], list):
                                        if len(a['childquestionid']) > 0:
                                            if questionid in a['childquestionid']:
                                                a['childquestionid'].remove(questionid)
                                                if len(a['childquestionid']) == 0:
                                                    a['childquestionid'] = 0
                                    else:
                                        if questionid == a['childquestionid']:
                                            a['childquestionid'] = 0
                            parentdata.first().answers = newanswers
                            parentdata.first().islocked = 0
                            parentdata.first().modifiedby = session['empid']
                            db.session.add(parentdata.first())
                            db.session.commit()
                            parentdata = Question.query.filter_by(id=parentid)
                            result = [{col: getattr(d, col) for col in colsquestion} for d in parentdata]
                            parentquesdataafter = result[0]
                            # region call audit trail method
                            auditins = Audittrail("QUESTION", "UPDATE", str(parentquesdatabefore),
                                                  str(parentquesdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                        return make_response(
                            jsonify({"msg": f"Question with ID {questionid} successfully deleted."})), 204
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@question.route('/api/viewquestion', methods=['POST'])
def viewquestion():
    """
        ---
        post:
          description: View question(s) using required filters.
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
              - viewquestions
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
                    proj_id = res['proj_id']
                    area_id = res['area_id']
                    func_id = res['func_id']
                    if 'subfunc_id' in res:
                        subfunc_id = res['subfunc_id']
                        data = Question.query.filter(Question.proj_id == proj_id, Question.area_id == area_id,
                                                     Question.func_id == func_id, Question.subfunc_id == subfunc_id,
                                                     Question.isdependentquestion == 0)
                    else:
                        data = Question.query.filter(Question.proj_id == proj_id, Question.area_id == area_id,
                                                     Question.func_id == func_id, Question.isdependentquestion == 0)
                    lists = []
                    for user in data:
                        json_data = {'question_id': user.id, 'question_name': user.name,
                                     'answer_type': user.answer_type, 'maxscore': user.maxscore,
                                     'answers': user.answers, 'proj_id': user.proj_id, 'area_id': user.area_id,
                                     'func_id': user.func_id, 'subfunc_id': user.subfunc_id,
                                     'mandatory': user.mandatory,
                                     'updationdatetime': user.updationdatetime,
                                     'isdependentquestion': user.isdependentquestion}
                        lists.append(json_data)
                    childquesidlist = []
                    for i in range(len(lists)):
                        for j in lists[i]["answers"]:
                            if j["childquestionid"] != 0:
                                if isinstance(j["childquestionid"], list):
                                    for k in j["childquestionid"]:
                                        childquesidlist.append(k)
                                else:
                                    childquesidlist.append(j["childquestionid"])
                    for c in childquesidlist:
                        for i in range(len(lists)):
                            if lists[i]["question_id"] == c:
                                lists.pop(i)
                                break
                    return make_response(jsonify({"data": lists})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@question.route('/api/updatequesasdependent', methods=['PUT'])
def updatequesasdependent():
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == 'PUT':
                    res = request.get_json(force=True)
                    if type(res['question']) is list:
                        ques = res['question']
                        for q in ques:
                            data = Question.query.filter_by(id=q['questionid'])
                            result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                            quesdatabefore = result[0]
                            result.clear()
                            if data.first() is not None:
                                data.first().isdependentquestion = q['isdependentquestion']
                                data.first().modifiedby = session['empid']
                                data.first().islocked = 0
                                db.session.add(data.first())
                                db.session.commit()
                                data = Question.query.filter_by(id=q['questionid'])
                                result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                quesdataafter = result[0]
                                # region call audit trail method
                                auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore),
                                                      str(quesdataafter),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                    else:
                        questionid = res['questionid']
                        data = Question.query.filter_by(id=questionid)
                        result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                        quesdatabefore = result[0]
                        result.clear()
                        if data.first() is not None:
                            data.first().isdependentquestion = res['isdependentquestion']
                            data.first().modifiedby = session['empid']
                            data.first().islocked = 0
                            db.session.add(data.first())
                            db.session.commit()
                            data = Question.query.filter_by(id=questionid)
                            result = [{col: getattr(d, col) for col in colsquestion} for d in data]
                            quesdataafter = result[0]
                            # region call audit trail method
                            auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore),
                                                  str(quesdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                    return make_response(jsonify({"msg": "Question marked as dependent or non-dependent "
                                                         "successfully."})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
