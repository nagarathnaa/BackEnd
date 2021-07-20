import datetime
from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.assessment_model import Assessment
from DOEAssessmentApp.DOE_models.project_model import Project
from DOEAssessmentApp.DOE_models.area_model import Area
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.trn_team_member_assessment_model import QuestionsAnswered
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.smtp_integration import trigger_mail
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail

assessment = Blueprint('assessment', __name__)


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@assessment.route('/api/submitassessment', methods=['PUT'])
def submitassessment():
    try:
        results = []
        totalscoreachieved = 0
        totalmaxscore = 0
        retakedatetime = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "PUT":
                    res = request.get_json(force=True)
                    isdraft = res['isdraft']
                    projid = res['projectid']
                    managerdata = Projectassignmenttomanager.query.filter_by(project_id=projid, status=1).first()
                    empid = res['emp_id']
                    userdata = Companyuserdetails.query.filter_by(empid=empid).first()
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

                    areaid = res['area_id']
                    funcid = res['functionality_id']
                    if "subfunc_id" in res:
                        subfuncid = res['subfunc_id']
                        dataforretake = Subfunctionality.query.filter_by(id=subfuncid).first()
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid) + str(subfuncid)
                    else:
                        dataforretake = Functionality.query.filter_by(id=funcid).first()
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid)
                    existing_assessment = Assessment.query.filter_by(combination=combination, active=1).first()
                    assessmentid = existing_assessment.id
                    data = Assessment.query.filter_by(id=assessmentid)
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'emp_id': d.emp_id},
                                              {'projectid': d.projectid},
                                              {'area_id': d.area_id},
                                              {'employeeassignedstatus': d.employeeassignedstatus},
                                              {'combination': d.combination},
                                              {'totalmaxscore': d.totalmaxscore},
                                              {'totalscoreachieved': d.totalscoreachieved},
                                              {'countoftotalquestions': d.countoftotalquestions},
                                              {'comment': d.comment},
                                              {'assessmentstatus': d.assessmentstatus},
                                              {'assessmenttakendatetime': d.assessmenttakendatetime},
                                              {'assessmentrevieweddatetime': d.assessmentrevieweddatetime},
                                              {'assessmentretakedatetime': d.assessmentretakedatetime},
                                              {'active': d.active},
                                              {'creationdatetime': d.creationdatetime},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    asessmentdatabefore = results[0]
                    results.clear()
                    checkifeligibledata = Assessment.query.filter_by(id=assessmentid).first()
                    if checkifeligibledata.assessmentretakedatetime is not None and \
                            (checkifeligibledata.assessmentretakedatetime.
                             replace(microsecond=0) - datetime.datetime.now().
                             replace(microsecond=0)).total_seconds() > 0:
                        return make_response(jsonify({"msg": "Your are not allowed to take the assessment "
                                                             "now!! Please take it on " + str(checkifeligibledata.
                                                                                              assessmentretakedatetime.
                                                                                              replace(microsecond=0))})
                                             ), 200
                    else:
                        data_proj = Project.query.filter_by(id=projid).first()
                        assessmenttakendatetime = datetime.datetime.now()
                        if data_proj.needforreview == 0:
                            assessmentstatus = "COMPLETED"
                            if isdraft == 0:
                                # triggering a mail to team member with retake assessment date time
                                rah = dataforretake.retake_assessment_days
                                hours_added = datetime.timedelta(hours=rah)
                                retakedatetime = assessmenttakendatetime + hours_added

                                # region mail notification
                                notification_data = Notification.query.filter_by(
                                    event_name="SUBMITASSESSMENTWOREVIEW").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                    date=str(retakedatetime.replace(
                                                                                        microsecond=0)))
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region

                        else:
                            assessmentstatus = "PENDING FOR REVIEW"
                            if isdraft == 0:
                                # triggering a mail to team member to notify that the assessment submitted has
                                # gone for review

                                # region mail notification
                                notification_data = Notification.query.filter_by(
                                    event_name="SUBMITASSESSMENTWREVIEWTOTM").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname)
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region

                                # triggering a mail to reporting project manager with reviewing details
                                userdata = Companyuserdetails.query.filter_by(empid=managerdata.emp_id).first()
                                mailto_m = userdata.empemail
                                mailtoname_m = userdata.empname
                                # region mail notification
                                notification_data = Notification.query.filter_by(
                                    event_name="SUBMITASSESSMENTWREVIEWTOMANAGER").first()
                                mail_subject = str(notification_data.mail_subject).format(empname=empname)
                                mail_body = str(notification_data.mail_body).format(managername=mailtoname_m,
                                                                                    empname=empname)
                                mailout = trigger_mail(mailfrom, mailto_m, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region
                        qadata = QuestionsAnswered.query.filter_by(assignmentid=assessmentid)
                        if qadata.first() is not None:
                            for qa in qadata:
                                eachqadata = QuestionsAnswered.query.filter_by(id=qa.id)
                                for d in eachqadata:
                                    json_data = mergedict({'id': d.id},
                                                          {'qid': d.qid},
                                                          {'applicability': d.applicability},
                                                          {'answers': d.answers},
                                                          {'scoreachieved': d.scoreachieved},
                                                          {'maxscore': d.maxscore},
                                                          {'assignmentid': d.assignmentid},
                                                          {'comment': d.comment},
                                                          {'active': d.active},
                                                          {'creationdatetime': d.creationdatetime},
                                                          {'updationdatetime': d.updationdatetime},
                                                          {'createdby': d.createdby},
                                                          {'modifiedby': d.modifiedby})
                                    results.append(json_data)
                                questionanswerdatabefore = results[0]
                                results.clear()
                                eachqadata.first().active = 0
                                eachqadata.first().modifiedby = session['empid']
                                db.session.add(eachqadata.first())
                                db.session.commit()
                                eachqadata = QuestionsAnswered.query.filter_by(id=qa.id)
                                for d in eachqadata:
                                    json_data = mergedict({'id': d.id},
                                                          {'qid': d.qid},
                                                          {'applicability': d.applicability},
                                                          {'answers': d.answers},
                                                          {'scoreachieved': d.scoreachieved},
                                                          {'maxscore': d.maxscore},
                                                          {'assignmentid': d.assignmentid},
                                                          {'comment': d.comment},
                                                          {'active': d.active},
                                                          {'creationdatetime': d.creationdatetime},
                                                          {'updationdatetime': d.updationdatetime},
                                                          {'createdby': d.createdby},
                                                          {'modifiedby': d.modifiedby})
                                    results.append(json_data)
                                questionanswerdataafter = results[0]
                                # region call audit trail method
                                auditins = Audittrail("QUESTION ANSWER", "UPDATE", str(questionanswerdatabefore),
                                                      str(questionanswerdataafter),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                results.clear()
                                # end region
                        questions = res['Questions']
                        for q in questions:
                            qid = q['QID']
                            applicability = q['applicability']
                            options = q['answers']
                            comment = q['comment']
                            if applicability == 1:
                                scoreachieved = q['scoreachieved']
                                maxscore = q['maxscore']
                            else:
                                scoreachieved = 0
                                maxscore = 0
                            totalscoreachieved = totalscoreachieved + scoreachieved
                            totalmaxscore = totalmaxscore + maxscore
                            quesanssubmit = QuestionsAnswered(qid, applicability, options, scoreachieved, maxscore,
                                                              assessmentid, comment, session['empid'])
                            db.session.add(quesanssubmit)
                            db.session.commit()
                            data = QuestionsAnswered.query.filter_by(id=quesanssubmit.id)
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'qid': d.qid},
                                                      {'applicability': d.applicability},
                                                      {'answers': d.answers},
                                                      {'scoreachieved': d.scoreachieved},
                                                      {'maxscore': d.maxscore},
                                                      {'assignmentid': d.assignmentid},
                                                      {'comment': d.comment},
                                                      {'active': d.active},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                results.append(json_data)
                            # region call audit trail method
                            auditins = Audittrail("QUESTION ANSWER", "ADD", None, str(results[0]), session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            results.clear()
                            # end region
                        data = Assessment.query.filter_by(id=assessmentid)
                        if data.first() is not None:
                            data.first().assessmentstatus = assessmentstatus if isdraft == 0 else "INCOMPLETE"
                            data.first().comment = None
                            data.first().totalmaxscore = totalmaxscore
                            data.first().totalscoreachieved = totalscoreachieved
                            data.first().assessmenttakendatetime = assessmenttakendatetime
                            data.first().assessmentretakedatetime = retakedatetime if isdraft == 0 else None
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()
                            data = Assessment.query.filter_by(id=assessmentid)
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'emp_id': d.emp_id},
                                                      {'projectid': d.projectid},
                                                      {'area_id': d.area_id},
                                                      {'employeeassignedstatus': d.employeeassignedstatus},
                                                      {'combination': d.combination},
                                                      {'totalmaxscore': d.totalmaxscore},
                                                      {'totalscoreachieved': d.totalscoreachieved},
                                                      {'countoftotalquestions': d.countoftotalquestions},
                                                      {'comment': d.comment},
                                                      {'assessmentstatus': d.assessmentstatus},
                                                      {'assessmenttakendatetime': d.assessmenttakendatetime},
                                                      {'assessmentrevieweddatetime': d.assessmentrevieweddatetime},
                                                      {'assessmentretakedatetime': d.assessmentretakedatetime},
                                                      {'active': d.active},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                results.append(json_data)
                            assessmentdataafter = results[0]
                            # region call audit trail method
                            auditins = Audittrail("ASSESSMENT", "UPDATE", str(asessmentdatabefore),
                                                  str(assessmentdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                        if isdraft == 0:
                            return make_response(jsonify({"msg": "Assessment submitted successfully!!"})), 200
                        else:

                            # region mail notification
                            notification_data = Notification.query.filter_by(
                                event_name="SAVEASDRAFTTOTM").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                            return make_response(jsonify({"msg": "Assessment saved as draft successfully!!"})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assessment.route('/api/reviewassessment', methods=['PUT'])
def reviewassessment():
    try:
        results = []
        retakedatetime = None
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if 'empid' in session and Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "PUT":
                    res = request.get_json(force=True)
                    comment = res['managerscomment']
                    projid = res['projectid']
                    empid = res['emp_id']
                    userdata = Companyuserdetails.query.filter_by(empid=empid).first()
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
                    areaid = res['area_id']
                    funcid = res['functionality_id']
                    if "subfunc_id" in res:
                        subfuncid = res['subfunc_id']
                        dataforretake = Subfunctionality.query.filter_by(id=subfuncid).first()
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid) + str(subfuncid)
                    else:
                        dataforretake = Functionality.query.filter_by(id=funcid).first()
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid)
                    existing_assessment = Assessment.query.filter_by(combination=combination, active=1).first()
                    assessmentid = existing_assessment.id
                    data = Assessment.query.filter_by(id=assessmentid)
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'emp_id': d.emp_id},
                                              {'projectid': d.projectid},
                                              {'area_id': d.area_id},
                                              {'employeeassignedstatus': d.employeeassignedstatus},
                                              {'combination': d.combination},
                                              {'totalmaxscore': d.totalmaxscore},
                                              {'totalscoreachieved': d.totalscoreachieved},
                                              {'countoftotalquestions': d.countoftotalquestions},
                                              {'comment': d.comment},
                                              {'assessmentstatus': d.assessmentstatus},
                                              {'assessmenttakendatetime': d.assessmenttakendatetime},
                                              {'assessmentrevieweddatetime': d.assessmentrevieweddatetime},
                                              {'assessmentretakedatetime': d.assessmentretakedatetime},
                                              {'active': d.active},
                                              {'creationdatetime': d.creationdatetime},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    asessmentdatabefore = results[0]
                    results.clear()
                    if res['assessmentstatus'] == 'REJECTED':
                        assessmentstatus = 'PENDING'
                        # triggering a mail to team member to notify that the assessment submitted has been rejected

                        # region mail notification
                        notification_data = Notification.query.filter_by(
                            event_name="ASSESSMENTREJECTED").first()
                        mail_subject = notification_data.mail_subject
                        mail_body = str(notification_data.mail_body).format(empname=empname)
                        mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region

                    else:
                        assessmentstatus = 'COMPLETED'  # when ACCEPTED
                        # triggering a mail to team member with retake assessment date time
                        rah = dataforretake.retake_assessment_days
                        hours_added = datetime.timedelta(hours=rah)
                        retakedatetime = data.first().assessmenttakendatetime + hours_added

                        # region mail notification
                        notification_data = Notification.query.filter_by(
                            event_name="ASSESSMENTACCEPTED").first()
                        mail_subject = notification_data.mail_subject
                        mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                            date=str(retakedatetime.replace(
                                                                                microsecond=0)))
                        mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                        print("======", mailout)
                        # end region

                    if data.first() is not None:
                        data.first().assessmentstatus = assessmentstatus
                        data.first().comment = comment
                        data.first().assessmentrevieweddatetime = datetime.datetime.now()
                        data.first().assessmentretakedatetime = retakedatetime
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()
                        assessment_datas = Assessment.query.filter_by(id=assessmentid)
                        for d in assessment_datas:
                            json_data = mergedict({'id': d.id},
                                                  {'emp_id': d.emp_id},
                                                  {'projectid': d.projectid},
                                                  {'area_id': d.area_id},
                                                  {'employeeassignedstatus': d.employeeassignedstatus},
                                                  {'combination': d.combination},
                                                  {'totalmaxscore': d.totalmaxscore},
                                                  {'totalscoreachieved': d.totalscoreachieved},
                                                  {'countoftotalquestions': d.countoftotalquestions},
                                                  {'comment': d.comment},
                                                  {'assessmentstatus': d.assessmentstatus},
                                                  {'assessmenttakendatetime': d.assessmenttakendatetime},
                                                  {'assessmentrevieweddatetime': d.assessmentrevieweddatetime},
                                                  {'assessmentretakedatetime': d.assessmentretakedatetime},
                                                  {'active': d.active},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        assessmentdataafter = results[0]
                        # region call audit trail method
                        auditins = Audittrail("ASSESSMENT", "UPDATE", str(asessmentdatabefore),
                                              str(assessmentdataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                    return make_response(jsonify({"msg": "Thank you for reviewing the assessment!!"})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assessment.route('/api/dashboard', methods=['POST'])
def getdashboard():
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
                    emp_id = res['emp_id']
                    data = Assessment.query.filter(Assessment.emp_id == emp_id, Assessment.employeeassignedstatus == 1,
                                                   Assessment.active == 1)
                    results = []
                    for user in data:
                        project_data = Project.query.filter(Project.id == user.projectid)
                        area_data = Area.query.filter(Area.id == user.area_id)
                        functionality_data = Functionality.query.filter(
                            Functionality.id == user.functionality_id)
                        if project_data.first() is not None and area_data.first() is not \
                                None and functionality_data.first() is not None:
                            if user.subfunctionality_id is None:
                                json_data = {'assessid': user.id, 'projectid': user.projectid,
                                             'project_name': project_data.first().name,
                                             'needforreview': project_data.first().needforreview,
                                             'area_id': user.area_id,
                                             'area_name': area_data.first().name,
                                             'functionality_id': user.functionality_id,
                                             'functionality_name': functionality_data.first().name,
                                             'totalscoreachieved': user.totalscoreachieved,
                                             'assessmentstatus': user.assessmentstatus,
                                             'comment': user.comment,
                                             'retakedatetime': user.assessmentretakedatetime}
                                results.append(json_data)
                            else:
                                subfunctionality_data = Subfunctionality.query.filter(
                                    Subfunctionality.id == user.subfunctionality_id)
                                if subfunctionality_data.first() is not None:
                                    json_data = {'assessid': user.id, 'projectid': user.projectid,
                                                 'project_name': project_data.first().name,
                                                 'needforreview': project_data.first().needforreview,
                                                 'area_id': user.area_id,
                                                 'area_name': area_data.first().name,
                                                 'functionality_id': user.functionality_id,
                                                 'functionality_name': functionality_data.first().name,
                                                 'subfunctionality_id': user.subfunctionality_id,
                                                 'subfunctionality_name': subfunctionality_data.first().name,
                                                 'totalscoreachieved': user.totalscoreachieved,
                                                 'assessmentstatus': user.assessmentstatus,
                                                 'comment': user.comment,
                                                 'retakedatetime': user.assessmentretakedatetime}
                                    results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assessment.route('/api/assessmenttaking', methods=['POST'])
def getassessmenttaking():
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
                    empid = res['emp_id']
                    area_id = res['area_id']
                    func_id = res['func_id']
                    if 'subfunc_id' in res:
                        subfunc_id = res['subfunc_id']
                        combination = str(empid) + str(proj_id) + str(area_id) + str(func_id) + str(subfunc_id)
                        data = Question.query.filter_by(proj_id=proj_id, area_id=area_id,
                                                        func_id=func_id, subfunc_id=subfunc_id,
                                                        isdependentquestion=0,
                                                        islocked=1).order_by(Question.id)
                    else:
                        combination = str(empid) + str(proj_id) + str(area_id) + str(func_id)
                        data = Question.query.filter_by(proj_id=proj_id, area_id=area_id,
                                                        func_id=func_id, subfunc_id=None,
                                                        isdependentquestion=0,
                                                        islocked=1).order_by(Question.id)
                    existing_assessment = Assessment.query.filter_by(combination=combination, employeeassignedstatus=1,
                                                                     active=1).first()
                    if existing_assessment is not None:
                        assessmentid = existing_assessment.id
                        checkifeligibledata = Assessment.query.filter_by(id=assessmentid).first()
                        if checkifeligibledata.assessmentstatus == "INCOMPLETE":
                            questions_answer = QuestionsAnswered.query.filter_by(assignmentid=assessmentid,
                                                                                 active=1).order_by(QuestionsAnswered.
                                                                                                    qid).all()
                            lists = []
                            for user in questions_answer:
                                qdata = Question.query.filter(Question.id == user.qid)
                                if qdata.first() is not None:
                                    lists.append(
                                        {'question_id': user.qid, 'question_name': qdata.first().name,
                                         'answers': user.answers, 'maxscore': qdata.first().maxscore,
                                         'scoreachieved': user.scoreachieved, 'answer_type': qdata.first().answer_type,
                                         'applicability': user.applicability, 'comment': user.comment,
                                         'mandatory': qdata.first().mandatory,
                                         'isdependentquestion': qdata.first().isdependentquestion})
                            return make_response(jsonify({"data": lists})), 200
                        elif checkifeligibledata.assessmentstatus == "PENDING FOR REVIEW":
                            return make_response(jsonify({"msg": "You can not retake the assessment now!! It has"
                                                                 " gone for manager's review."})), 200
                        else:
                            if checkifeligibledata.assessmentretakedatetime is not None and \
                                    (checkifeligibledata.assessmentretakedatetime.replace(microsecond=0) - datetime.
                                     datetime.now().replace(microsecond=0)).total_seconds() > 0:
                                rtm = checkifeligibledata.assessmentretakedatetime.replace(microsecond=0)
                                return make_response(jsonify({"msg": "Your are not allowed to take the assessment "
                                                                     "now!! Please take it on " + str(rtm)})), 200
                            else:
                                lists = []
                                for user in data:
                                    lists.append(
                                        {'question_id': user.id, 'question_name': user.name,
                                         'answer_type': user.answer_type,
                                         'answers': user.answers, 'maxscore': user.maxscore,
                                         'mandatory': user.mandatory, 'isdependentquestion': user.isdependentquestion})
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
                        return make_response(jsonify({"msg": "No assessments assigned to you in this category."
                                                             " Please select a different project or area or "
                                                             "functionality or subfunctionality."})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assessment.route('/api/achvperclevelacpercbyteammember', methods=['POST'])
def achvperclevelacpercbyteammember():
    try:
        scoreachievedbytmfortheproject = 0
        maxscorefortheproject = 0
        countofquestions = 0
        countofnaques = 0
        countofquestionanswered = 0
        achievedlevel = ''
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
                    projid = res['projectid']
                    empid = res['emp_id']
                    assessdata = Assessment.query.filter(Assessment.emp_id == empid, Assessment.projectid == projid,
                                                         Assessment.assessmentstatus == "COMPLETED",
                                                         Assessment.active == 1,
                                                         Assessment.employeeassignedstatus == 1)
                    if assessdata.first() is not None:
                        for a in assessdata:
                            scoreachievedbytmfortheproject = scoreachievedbytmfortheproject + a.totalscoreachieved
                            maxscorefortheproject = maxscorefortheproject + a.totalmaxscore
                            countofquestions = countofquestions + a.countoftotalquestions
                            cofquesanswdperassessment = QuestionsAnswered.query.filter_by(assignmentid=a.id,
                                                                                          active=1,
                                                                                          applicability=1).count()
                            cofnaquesperassessment = QuestionsAnswered.query.filter_by(assignmentid=a.id,
                                                                                       active=1,
                                                                                       applicability=0).count()
                            countofnaques = countofnaques + cofnaquesperassessment
                            countofquestionanswered = countofquestionanswered + cofquesanswdperassessment
                        if countofnaques != 0:
                            countofquestions = countofquestions - countofnaques
                        if countofquestions != 0:
                            assessmentcompletion = (countofquestionanswered / countofquestions) * 100
                            achievedpercentage = (scoreachievedbytmfortheproject / maxscorefortheproject) * 100
                        else:
                            assessmentcompletion = 0
                            achievedpercentage = 0
                        leveldata = Project.query.filter(Project.id == projid)
                        if leveldata.first() is not None:
                            for lev in leveldata.first().levels:
                                if (achievedpercentage >= lev['RangeFrom']) and (
                                        achievedpercentage <= lev['RangeTo']):
                                    achievedlevel = lev['LevelName']
                                    break
                        else:
                            achievedlevel = ''
                        return make_response(jsonify({"achievedpercentage": str(achievedpercentage),
                                                      "achievedlevel": achievedlevel,
                                                      "assessmentcompletion": str(assessmentcompletion)})), 200
                    else:
                        return make_response(jsonify({"msg": "No assessment data found!!"})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assessment.route('/api/viewuserassessmentresult', methods=['POST'])
def viewuserassessmentresult():
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
                    projid = res['projectid']
                    empid = res['emp_id']
                    areaid = res['area_id']
                    funcid = res['functionality_id']
                    if "subfunc_id" in res:
                        subfuncid = res['subfunc_id']
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid) + str(subfuncid)
                    else:
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid)
                    tobeassessed_datafound = Assessment.query.filter(
                        Assessment.combination == combination, Assessment.assessmentstatus != "NEW",
                        Assessment.assessmentstatus != "COMPLETED", Assessment.assessmentstatus != "PENDING",
                        Assessment.assessmentstatus != "INCOMPLETE",
                        Assessment.active == 1)
                    if tobeassessed_datafound.first() is not None:
                        questions_answer = QuestionsAnswered.query.filter_by(assignmentid=tobeassessed_datafound.
                                                                             first().id,
                                                                             active=1).all()
                        lists = []
                        for user in questions_answer:
                            qdata = Question.query.filter(Question.id == user.qid)
                            if qdata.first() is not None:
                                lists.append(
                                    {'question_id': user.qid, 'question_name': qdata.first().name,
                                     'questions_answers': user.answers,
                                     'scoreachieved': user.scoreachieved, 'answer_type': qdata.first().answer_type,
                                     'applicability': user.applicability, 'comment': user.comment})
                        return make_response(jsonify({"data": lists})), 200
                    else:
                        return make_response(jsonify({"msg": "No Assessments to review!!"})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assessment.route('/api/viewassessmenttakenbytm', methods=['POST'])
def viewassessmenttakenbytm():
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
                    projid = res['projectid']
                    empid = res['emp_id']
                    areaid = res['area_id']
                    funcid = res['functionality_id']
                    if "subfunc_id" in res:
                        subfuncid = res['subfunc_id']
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid) + str(subfuncid)
                    else:
                        combination = str(empid) + str(projid) + str(areaid) + str(funcid)
                    tobeassessed_datafound = Assessment.query.filter(Assessment.combination == combination,
                                                                     Assessment.assessmentstatus != "NEW",
                                                                     Assessment.active == 1)
                    if tobeassessed_datafound.first() is not None:
                        questions_answer = QuestionsAnswered.query.filter_by(assignmentid=tobeassessed_datafound.
                                                                             first().id,
                                                                             active=1).all()
                        lists = []
                        for user in questions_answer:
                            qdata = Question.query.filter(Question.id == user.qid)
                            if qdata.first() is not None:
                                lists.append(
                                    {'question_id': user.qid, 'question_name': qdata.first().name,
                                     'questions_answers': user.answers,
                                     'scoreachieved': user.scoreachieved, 'answer_type': qdata.first().answer_type,
                                     'applicability': user.applicability, 'comment': user.comment})
                        return make_response(jsonify({"data": lists})), 200
                    else:
                        return make_response(jsonify({"msg": "This assessment is yet to be taken!!"})), 400
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
