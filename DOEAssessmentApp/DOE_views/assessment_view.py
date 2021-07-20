from flask import Blueprint, session, request, jsonify, make_response
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.assessment_model import Assessment
from DOEAssessmentApp.DOE_models.project_model import Project
from DOEAssessmentApp.DOE_models.area_model import Area
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

# from DOEAssessmentApp.trigger_notification import handle_message

assigningteammember = Blueprint('assigningteammember', __name__)

colsquestion = ['id', 'name', 'answer_type', 'answers', 'maxscore', 'subfunc_id', 'func_id', 'area_id', 'proj_id',
                'combination', 'mandatory', 'islocked', 'isdependentquestion',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


@assigningteammember.route('/api/assigningteammember', methods=['GET', 'POST'])
def getandpost():
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
                    results = []
                    data = Assessment.query.filter_by(active=1).all()
                    for user in data:
                        userdata = Companyuserdetails.query.filter_by(empid=user.emp_id)
                        data_proj = Project.query.filter_by(id=user.projectid)
                        data_area = Area.query.filter_by(id=user.area_id)
                        data_func = Functionality.query.filter_by(id=user.functionality_id)
                        if userdata.first() is not None and data_proj.first() is not None and data_area.first() is not \
                                None and data_func.first() is not None:
                            if user.subfunctionality_id is not None:
                                data_subfunc = Subfunctionality.query.filter_by(id=user.subfunctionality_id)
                                if data_subfunc.first() is not None:
                                    json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                 'emp_name': userdata.first().empname,
                                                 'project_id': user.projectid, 'project_name': data_proj.first().name,
                                                 'area_id': user.area_id, 'area_name': data_area.first().name,
                                                 'functionality_id': user.functionality_id,
                                                 'func_name': data_func.first().name,
                                                 'subfunctionality_id': user.subfunctionality_id,
                                                 'subfunc_name': data_subfunc.first().name,
                                                 'employeeassignedstatus': user.employeeassignedstatus,
                                                 'totalmaxscore': user.totalmaxscore,
                                                 'totalscoreachieved': user.totalscoreachieved,
                                                 'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                                 'assessmenttakendatetime': user.assessmenttakendatetime,
                                                 'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                 'active': user.active,
                                                 'creationdatetime': user.creationdatetime,
                                                 'updationdatetime': user.updationdatetime}
                                    results.append(json_data)
                            else:
                                json_data = {'id': user.id, 'emp_id': user.emp_id, 'emp_name': userdata.first().empname,
                                             'project_id': user.projectid, 'project_name': data_proj.first().name,
                                             'area_id': user.area_id, 'area_name': data_area.first().name,
                                             'functionality_id': user.functionality_id,
                                             'func_name': data_func.first().name,
                                             'employeeassignedstatus': user.employeeassignedstatus,
                                             'totalmaxscore': user.totalmaxscore,
                                             'totalscoreachieved': user.totalscoreachieved,
                                             'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                             'assessmenttakendatetime': user.assessmenttakendatetime,
                                             'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                             'active': user.active,
                                             'creationdatetime': user.creationdatetime,
                                             'updationdatetime': user.updationdatetime}
                                results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
                elif request.method == "POST":
                    res = request.get_json(force=True)
                    assessmentstatus = 'NEW'
                    team_empid = res['emp_id']
                    projid = res['projectid']

                    userdata = Companyuserdetails.query.filter_by(empid=team_empid).first()
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

                    if 'functionality' in res and type(res['functionality']) is list:
                        funcid = res['functionality']
                        for f in funcid:
                            func_data = Functionality.query.filter_by(id=f['functionality_id']).first()
                            func_name = func_data.name
                            subfuncid = None
                            combination = str(team_empid) + str(projid) + str(f['area_id']) + str(f['functionality_id'])
                            adata = Assessment.query.filter_by(combination=combination)
                            if adata.first() is not None:
                                for a in adata:
                                    eachadata = Assessment.query.filter_by(id=a.id)
                                    for user in eachadata:
                                        json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                     'project_id': user.projectid,
                                                     'area_id': user.area_id,
                                                     'functionality_id': user.functionality_id,
                                                     'employeeassignedstatus': user.employeeassignedstatus,
                                                     'totalmaxscore': user.totalmaxscore,
                                                     'totalscoreachieved': user.totalscoreachieved,
                                                     'comment': user.comment,
                                                     'assessmentstatus': user.assessmentstatus,
                                                     'assessmenttakendatetime': user.assessmenttakendatetime,
                                                     'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                     'active': user.active,
                                                     'creationdatetime': user.creationdatetime,
                                                     'updationdatetime': user.updationdatetime,
                                                     'createdby': user.createdby,
                                                     'modifiedby': user.modifiedby}
                                        result.append(json_data)
                                    assessdatabefore = result[0]
                                    result.clear()
                                    eachadata.first().active = 0
                                    eachadata.first().modifiedby = session['empid']
                                    db.session.add(eachadata.first())
                                    db.session.commit()
                                    eachadata = Assessment.query.filter_by(id=a.id)
                                    for user in eachadata:
                                        json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                     'project_id': user.projectid,
                                                     'area_id': user.area_id,
                                                     'functionality_id': user.functionality_id,
                                                     'employeeassignedstatus': user.employeeassignedstatus,
                                                     'totalmaxscore': user.totalmaxscore,
                                                     'totalscoreachieved': user.totalscoreachieved,
                                                     'comment': user.comment,
                                                     'assessmentstatus': user.assessmentstatus,
                                                     'assessmenttakendatetime': user.assessmenttakendatetime,
                                                     'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                     'active': user.active,
                                                     'creationdatetime': user.creationdatetime,
                                                     'updationdatetime': user.updationdatetime,
                                                     'createdby': user.createdby,
                                                     'modifiedby': user.modifiedby}
                                        result.append(json_data)
                                    assessdataafter = result[0]
                                    result.clear()
                                    # region call audit trail method
                                    auditins = Audittrail("ASSESSMENT", "UPDATE", str(assessdatabefore),
                                                          str(assessdataafter),
                                                          session['empid'])
                                    db.session.add(auditins)
                                    db.session.commit()
                                    # end region
                            countoftotalquestions = Question.query.filter_by(proj_id=projid, area_id=f['area_id'],
                                                                             func_id=f['functionality_id']).count()
                            assessmentins = Assessment(team_empid, projid, f['area_id'], f['functionality_id'],
                                                       subfuncid, combination, assessmentstatus,
                                                       countoftotalquestions, session['empid'])
                            db.session.add(assessmentins)
                            db.session.commit()
                            assessdata = Assessment.query.filter_by(id=assessmentins.id)
                            for data in assessdata:
                                json_data = {'id': data.id, 'emp_id': data.emp_id,
                                             'project_id': data.projectid,
                                             'area_id': data.area_id,
                                             'functionality_id': data.functionality_id,
                                             'employeeassignedstatus': data.employeeassignedstatus,
                                             'totalmaxscore': data.totalmaxscore,
                                             'totalscoreachieved': data.totalscoreachieved,
                                             'comment': data.comment,
                                             'assessmentstatus': data.assessmentstatus,
                                             'assessmenttakendatetime': data.assessmenttakendatetime,
                                             'assessmentrevieweddatetime': data.assessmentrevieweddatetime,
                                             'active': data.active,
                                             'creationdatetime': data.creationdatetime,
                                             'updationdatetime': data.updationdatetime,
                                             'createdby': data.createdby,
                                             'modifiedby': data.modifiedby}
                                result.append(json_data)
                            # region call audit trail method
                            auditins = Audittrail("ASSESSMENT", "ADD", None,
                                                  str(result[0]),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region

                            result.clear()

                            # region mail notification
                            notification_data = Notification.query.filter_by(
                                event_name="ASSESSMENTASSIGNMENT").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                name=func_name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname,
                                                   mail_body)
                            print("======", mailout)
                            # end region

                            quesdata = Question.query.filter(Question.proj_id == projid,
                                                             Question.area_id == f['area_id'],
                                                             Question.func_id == f['functionality_id'])
                            for q in quesdata:
                                data = Question.query.filter_by(id=q.id)
                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                quesdatabefore = results[0]
                                results.clear()
                                data.first().islocked = 1
                                data.first().modifiedby = session['empid']
                                db.session.add(data.first())
                                db.session.commit()
                                data = Question.query.filter_by(id=q.id)
                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                quesdataafter = results[0]
                                # region call audit trail method
                                auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore),
                                                      str(quesdataafter),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                            data = Assessment.query.filter_by(id=assessmentins.id).first()
                            userdata = Companyuserdetails.query.filter_by(empid=data.emp_id).first()
                            data_proj = Project.query.filter_by(id=data.projectid).first()
                            data_area = Area.query.filter_by(id=data.area_id).first()
                            data_func = Functionality.query.filter_by(id=data.functionality_id).first()
                            result.append({'id': data.id, 'emp_id': data.emp_id, 'emp_name': userdata.empname,
                                           'project_id': data.projectid, 'project_name': data_proj.name,
                                           'area_id': data.area_id, 'area_name': data_area.name,
                                           'functionality_id': data.functionality_id, 'func_name': data_func.name,
                                           'employeeassignedstatus': data.employeeassignedstatus,
                                           'totalmaxscore': data.totalmaxscore,
                                           'totalscoreachieved': data.totalscoreachieved,
                                           'comment': data.comment, 'assessmentstatus': data.assessmentstatus,
                                           'assessmenttakendatetime': data.assessmenttakendatetime,
                                           'assessmentrevieweddatetime': data.assessmentrevieweddatetime,
                                           'creationdatetime': data.creationdatetime,
                                           'updationdatetime': data.updationdatetime})
                    else:
                        areaid = res['area_id']
                        funcid = res['functionality_id']
                        if "subfunc_id" in res:
                            if type(res['subfunc_id']) is list:
                                subfuncid = res['subfunc_id']
                                for s in subfuncid:
                                    subfunc_data = Subfunctionality.query.filter_by(id=s).first()
                                    subfunc_name = subfunc_data.name
                                    combination = str(team_empid) + str(projid) + str(areaid) + str(funcid) + str(s)
                                    adata = Assessment.query.filter_by(combination=combination)
                                    if adata.first() is not None:
                                        for a in adata:
                                            eachadata = Assessment.query.filter_by(id=a.id)
                                            for user in eachadata:
                                                json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                             'project_id': user.projectid,
                                                             'area_id': user.area_id,
                                                             'functionality_id': user.functionality_id,
                                                             'subfunctionality_id': user.subfunctionality_id,
                                                             'employeeassignedstatus': user.employeeassignedstatus,
                                                             'totalmaxscore': user.totalmaxscore,
                                                             'totalscoreachieved': user.totalscoreachieved,
                                                             'comment': user.comment,
                                                             'assessmentstatus': user.assessmentstatus,
                                                             'assessmenttakendatetime': user.assessmenttakendatetime,
                                                             'assessmentrevieweddatetime': user.
                                                             assessmentrevieweddatetime,
                                                             'active': user.active,
                                                             'creationdatetime': user.creationdatetime,
                                                             'updationdatetime': user.updationdatetime,
                                                             'createdby': user.createdby,
                                                             'modifiedby': user.modifiedby}
                                                result.append(json_data)
                                            assessdatabefore = result[0]
                                            result.clear()
                                            eachadata.first().active = 0
                                            eachadata.first().modifiedby = session['empid']
                                            db.session.add(eachadata.first())
                                            db.session.commit()
                                            eachadata = Assessment.query.filter_by(id=a.id)
                                            for user in eachadata:
                                                json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                             'project_id': user.projectid,
                                                             'area_id': user.area_id,
                                                             'functionality_id': user.functionality_id,
                                                             'subfunctionality_id': user.subfunctionality_id,
                                                             'employeeassignedstatus': user.employeeassignedstatus,
                                                             'totalmaxscore': user.totalmaxscore,
                                                             'totalscoreachieved': user.totalscoreachieved,
                                                             'comment': user.comment,
                                                             'assessmentstatus': user.assessmentstatus,
                                                             'assessmenttakendatetime': user.assessmenttakendatetime,
                                                             'assessmentrevieweddatetime': user.
                                                             assessmentrevieweddatetime,
                                                             'active': user.active,
                                                             'creationdatetime': user.creationdatetime,
                                                             'updationdatetime': user.updationdatetime,
                                                             'createdby': user.createdby,
                                                             'modifiedby': user.modifiedby}
                                                result.append(json_data)
                                            assessdataafter = result[0]
                                            result.clear()
                                            # region call audit trail method
                                            auditins = Audittrail("ASSESSMENT", "UPDATE", str(assessdatabefore),
                                                                  str(assessdataafter),
                                                                  session['empid'])
                                            db.session.add(auditins)
                                            db.session.commit()
                                            # end region
                                    countoftotalquestions = Question.query.filter_by(proj_id=projid,
                                                                                     area_id=areaid,
                                                                                     func_id=funcid,
                                                                                     subfunc_id=s).count()
                                    assessmentins = Assessment(team_empid, projid, areaid, funcid, s,
                                                               combination, assessmentstatus, countoftotalquestions,
                                                               session['empid'])
                                    db.session.add(assessmentins)
                                    db.session.commit()
                                    assessdata = Assessment.query.filter_by(id=assessmentins.id)
                                    for data in assessdata:
                                        json_data = {'id': data.id, 'emp_id': data.emp_id,
                                                     'project_id': data.projectid,
                                                     'area_id': data.area_id,
                                                     'functionality_id': data.functionality_id,
                                                     'subfunctionality_id': data.subfunctionality_id,
                                                     'employeeassignedstatus': data.employeeassignedstatus,
                                                     'totalmaxscore': data.totalmaxscore,
                                                     'totalscoreachieved': data.totalscoreachieved,
                                                     'comment': data.comment,
                                                     'assessmentstatus': data.assessmentstatus,
                                                     'assessmenttakendatetime': data.assessmenttakendatetime,
                                                     'assessmentrevieweddatetime': data.assessmentrevieweddatetime,
                                                     'active': data.active,
                                                     'creationdatetime': data.creationdatetime,
                                                     'updationdatetime': data.updationdatetime,
                                                     'createdby': data.createdby,
                                                     'modifiedby': data.modifiedby}
                                        result.append(json_data)
                                    # region call audit trail method
                                    auditins = Audittrail("ASSESSMENT", "ADD", None,
                                                          str(result[0]),
                                                          session['empid'])
                                    db.session.add(auditins)
                                    db.session.commit()
                                    # end region
                                    result.clear()

                                    # region mail notification
                                    notification_data = Notification.query.filter_by(
                                        event_name="ASSESSMENTASSIGNMENT").first()
                                    mail_subject = notification_data.mail_subject
                                    mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                        name=subfunc_name)
                                    mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname,
                                                           mail_body)
                                    print("======", mailout)
                                    # end region
                                    quesdata = Question.query.filter(Question.proj_id == projid,
                                                                     Question.area_id == areaid,
                                                                     Question.func_id == funcid,
                                                                     Question.subfunc_id == s)
                                    for q in quesdata:
                                        data = Question.query.filter_by(id=q.id)
                                        results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                        quesdatabefore = results[0]
                                        results.clear()
                                        data.first().islocked = 1
                                        data.first().modifiedby = session['empid']
                                        db.session.add(data.first())
                                        db.session.commit()
                                        data = Question.query.filter_by(id=q.id)
                                        results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                        quesdataafter = results[0]
                                        # region call audit trail method
                                        auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore),
                                                              str(quesdataafter),
                                                              session['empid'])
                                        db.session.add(auditins)
                                        db.session.commit()
                                        # end region
                                        results.clear()
                                    data = Assessment.query.filter_by(id=assessmentins.id).first()
                                    userdata = Companyuserdetails.query.filter_by(empid=data.emp_id).first()
                                    data_proj = Project.query.filter_by(id=data.projectid).first()
                                    data_area = Area.query.filter_by(id=data.area_id).first()
                                    data_func = Functionality.query.filter_by(id=data.functionality_id).first()
                                    data_subfunc = Subfunctionality.query.filter_by(
                                        id=data.subfunctionality_id).first()
                                    result.append(
                                        {'id': data.id, 'emp_id': data.emp_id, 'emp_name': userdata.empname,
                                         'project_id': data.projectid, 'project_name': data_proj.name,
                                         'area_id': data.area_id, 'area_name': data_area.name,
                                         'functionality_id': data.functionality_id,
                                         'func_name': data_func.name,
                                         'subfunctionality_id': data.subfunctionality_id,
                                         'subfunc_name': data_subfunc.name,
                                         'employeeassignedstatus': data.employeeassignedstatus,
                                         'totalmaxscore': data.totalmaxscore,
                                         'totalscoreachieved': data.totalscoreachieved,
                                         'comment': data.comment, 'assessmentstatus': data.assessmentstatus,
                                         'assessmenttakendatetime': data.assessmenttakendatetime,
                                         'assessmentrevieweddatetime': data.assessmentrevieweddatetime,
                                         'active': data.active,
                                         'creationdatetime': data.creationdatetime,
                                         'updationdatetime': data.updationdatetime,
                                         'createdby': data.createdby,
                                         'modifiedby': data.modifiedby})
                            else:
                                subfuncid = res['subfunc_id']
                                combination = str(team_empid) + str(projid) + str(areaid) + str(funcid) + str(subfuncid)
                                subfunc_data = Subfunctionality.query.filter_by(id=subfuncid).first()
                                subfunc_name = subfunc_data.name
                                adata = Assessment.query.filter_by(combination=combination)
                                if adata.first() is not None:
                                    for a in adata:
                                        eachadata = Assessment.query.filter_by(id=a.id)
                                        for user in eachadata:
                                            json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                         'project_id': user.projectid,
                                                         'area_id': user.area_id,
                                                         'functionality_id': user.functionality_id,
                                                         'subfunctionality_id': user.subfunctionality_id,
                                                         'employeeassignedstatus': user.employeeassignedstatus,
                                                         'totalmaxscore': user.totalmaxscore,
                                                         'totalscoreachieved': user.totalscoreachieved,
                                                         'comment': user.comment,
                                                         'assessmentstatus': user.assessmentstatus,
                                                         'assessmenttakendatetime': user.assessmenttakendatetime,
                                                         'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                         'active': user.active,
                                                         'creationdatetime': user.creationdatetime,
                                                         'updationdatetime': user.updationdatetime,
                                                         'createdby': user.createdby,
                                                         'modifiedby': user.modifiedby}
                                            result.append(json_data)
                                        assessdatabefore = result[0]
                                        result.clear()
                                        eachadata.first().active = 0
                                        eachadata.first().modifiedby = session['empid']
                                        db.session.add(eachadata.first())
                                        db.session.commit()
                                        eachadata = Assessment.query.filter_by(id=a.id)
                                        for user in eachadata:
                                            json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                         'project_id': user.projectid,
                                                         'area_id': user.area_id,
                                                         'functionality_id': user.functionality_id,
                                                         'subfunctionality_id': user.subfunctionality_id,
                                                         'employeeassignedstatus': user.employeeassignedstatus,
                                                         'totalmaxscore': user.totalmaxscore,
                                                         'totalscoreachieved': user.totalscoreachieved,
                                                         'comment': user.comment,
                                                         'assessmentstatus': user.assessmentstatus,
                                                         'assessmenttakendatetime': user.assessmenttakendatetime,
                                                         'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                         'active': user.active,
                                                         'creationdatetime': user.creationdatetime,
                                                         'updationdatetime': user.updationdatetime,
                                                         'createdby': user.createdby,
                                                         'modifiedby': user.modifiedby}
                                            result.append(json_data)
                                        assessdataafter = result[0]
                                        result.clear()
                                        # region call audit trail method
                                        auditins = Audittrail("ASSESSMENT", "UPDATE", str(assessdatabefore),
                                                              str(assessdataafter),
                                                              session['empid'])
                                        db.session.add(auditins)
                                        db.session.commit()
                                        # end region
                                countoftotalquestions = Question.query.filter_by(proj_id=projid,
                                                                                 area_id=areaid,
                                                                                 func_id=funcid,
                                                                                 subfunc_id=subfuncid).count()
                                assessmentins = Assessment(team_empid, projid, areaid, funcid, subfuncid,
                                                           combination, assessmentstatus, countoftotalquestions,
                                                           session['empid'])
                                db.session.add(assessmentins)
                                db.session.commit()
                                quesdata = Question.query.filter(Question.proj_id == projid,
                                                                 Question.area_id == areaid,
                                                                 Question.func_id == funcid,
                                                                 Question.subfunc_id == subfuncid)
                                for q in quesdata:
                                    data = Question.query.filter_by(id=q.id)
                                    results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                    quesdatabefore = results[0]
                                    results.clear()
                                    data.first().islocked = 1
                                    data.first().modifiedby = session['empid']
                                    db.session.add(data.first())
                                    db.session.commit()
                                    data = Question.query.filter_by(id=q.id)
                                    results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                    quesdataafter = results[0]
                                    # region call audit trail method
                                    auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore), str(quesdataafter),
                                                          session['empid'])
                                    db.session.add(auditins)
                                    db.session.commit()
                                    # end region
                                    results.clear()
                                data = Assessment.query.filter_by(id=assessmentins.id).first()
                                userdata = Companyuserdetails.query.filter_by(empid=data.emp_id).first()
                                data_proj = Project.query.filter_by(id=data.projectid).first()
                                data_area = Area.query.filter_by(id=data.area_id).first()
                                data_func = Functionality.query.filter_by(id=data.functionality_id).first()
                                data_subfunc = Subfunctionality.query.filter_by(id=data.subfunctionality_id).first()
                                result.append({'id': data.id, 'emp_id': data.emp_id, 'emp_name': userdata.empname,
                                               'project_id': data.projectid, 'project_name': data_proj.name,
                                               'area_id': data.area_id, 'area_name': data_area.name,
                                               'functionality_id': data.functionality_id,
                                               'func_name': data_func.name,
                                               'subfunctionality_id': data.subfunctionality_id,
                                               'subfunc_name': data_subfunc.name,
                                               'employeeassignedstatus': data.employeeassignedstatus,
                                               'totalmaxscore': data.totalmaxscore,
                                               'totalscoreachieved': data.totalscoreachieved,
                                               'comment': data.comment, 'assessmentstatus': data.assessmentstatus,
                                               'assessmenttakendatetime': data.assessmenttakendatetime,
                                               'assessmentrevieweddatetime': data.assessmentrevieweddatetime,
                                               'active': data.active,
                                               'creationdatetime': data.creationdatetime,
                                               'updationdatetime': data.updationdatetime,
                                               'createdby': data.createdby,
                                               'modifiedby': data.modifiedby})
                                # region call audit trail method
                                auditins = Audittrail("ASSESSMENT", "ADD", None,
                                                      str(result[0]),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region

                                # region mail notification
                                notification_data = Notification.query.filter_by(
                                    event_name="ASSESSMENTASSIGNMENT").first()
                                mail_subject = notification_data.mail_subject
                                mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                    name=subfunc_name)
                                mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                                print("======", mailout)
                                # end region
                        else:
                            subfuncid = None
                            combination = str(team_empid) + str(projid) + str(areaid) + str(funcid)
                            func_data = Functionality.query.filter_by(id=funcid).first()
                            func_name = func_data.name
                            adata = Assessment.query.filter_by(combination=combination)
                            if adata.first() is not None:
                                for a in adata:
                                    eachadata = Assessment.query.filter_by(id=a.id)
                                    for user in eachadata:
                                        json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                     'project_id': user.projectid,
                                                     'area_id': user.area_id,
                                                     'functionality_id': user.functionality_id,
                                                     'subfunctionality_id': user.subfunctionality_id,
                                                     'employeeassignedstatus': user.employeeassignedstatus,
                                                     'totalmaxscore': user.totalmaxscore,
                                                     'totalscoreachieved': user.totalscoreachieved,
                                                     'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                                     'assessmenttakendatetime': user.assessmenttakendatetime,
                                                     'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                     'active': user.active,
                                                     'creationdatetime': user.creationdatetime,
                                                     'updationdatetime': user.updationdatetime,
                                                     'createdby': user.createdby,
                                                     'modifiedby': user.modifiedby}
                                        result.append(json_data)
                                    assessdatabefore = result[0]
                                    result.clear()
                                    eachadata.first().active = 0
                                    eachadata.first().modifiedby = session['empid']
                                    db.session.add(eachadata.first())
                                    db.session.commit()
                                    eachadata = Assessment.query.filter_by(id=a.id)
                                    for user in eachadata:
                                        json_data = {'id': user.id, 'emp_id': user.emp_id,
                                                     'project_id': user.projectid,
                                                     'area_id': user.area_id,
                                                     'functionality_id': user.functionality_id,
                                                     'subfunctionality_id': user.subfunctionality_id,
                                                     'employeeassignedstatus': user.employeeassignedstatus,
                                                     'totalmaxscore': user.totalmaxscore,
                                                     'totalscoreachieved': user.totalscoreachieved,
                                                     'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                                     'assessmenttakendatetime': user.assessmenttakendatetime,
                                                     'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                                     'active': user.active,
                                                     'creationdatetime': user.creationdatetime,
                                                     'updationdatetime': user.updationdatetime,
                                                     'createdby': user.createdby,
                                                     'modifiedby': user.modifiedby}
                                        result.append(json_data)
                                    assessdataafter = result[0]
                                    result.clear()
                                    # region call audit trail method
                                    auditins = Audittrail("ASSESSMENT", "UPDATE", str(assessdatabefore),
                                                          str(assessdataafter),
                                                          session['empid'])
                                    db.session.add(auditins)
                                    db.session.commit()
                                    # end region
                            countoftotalquestions = Question.query.filter_by(proj_id=projid, area_id=areaid,
                                                                             func_id=funcid).count()
                            assessmentins = Assessment(team_empid, projid, areaid, funcid, subfuncid,
                                                       combination, assessmentstatus, countoftotalquestions,
                                                       session['empid'])
                            db.session.add(assessmentins)
                            db.session.commit()
                            quesdata = Question.query.filter(Question.proj_id == projid,
                                                             Question.area_id == areaid,
                                                             Question.func_id == funcid)
                            for q in quesdata:
                                data = Question.query.filter_by(id=q.id)
                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                quesdatabefore = results[0]
                                results.clear()
                                data.first().islocked = 1
                                data.first().modifiedby = session['empid']
                                db.session.add(data.first())
                                db.session.commit()
                                data = Question.query.filter_by(id=q.id)
                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                quesdataafter = results[0]
                                # region call audit trail method
                                auditins = Audittrail("QUESTION", "UPDATE", str(quesdatabefore), str(quesdataafter),
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                            data = Assessment.query.filter_by(id=assessmentins.id).first()
                            userdata = Companyuserdetails.query.filter_by(empid=data.emp_id).first()
                            data_proj = Project.query.filter_by(id=data.projectid).first()
                            data_area = Area.query.filter_by(id=data.area_id).first()
                            data_func = Functionality.query.filter_by(id=data.functionality_id).first()
                            result.append({'id': data.id, 'emp_id': data.emp_id, 'emp_name': userdata.empname,
                                           'project_id': data.projectid, 'project_name': data_proj.name,
                                           'area_id': data.area_id, 'area_name': data_area.name,
                                           'functionality_id': data.functionality_id, 'func_name': data_func.name,
                                           'employeeassignedstatus': data.employeeassignedstatus,
                                           'totalmaxscore': data.totalmaxscore,
                                           'totalscoreachieved': data.totalscoreachieved,
                                           'comment': data.comment, 'assessmentstatus': data.assessmentstatus,
                                           'assessmenttakendatetime': data.assessmenttakendatetime,
                                           'assessmentrevieweddatetime': data.assessmentrevieweddatetime,
                                           'active': data.active,
                                           'creationdatetime': data.creationdatetime,
                                           'updationdatetime': data.updationdatetime,
                                           'createdby': data.createdby,
                                           'modifiedby': data.modifiedby})
                            # region call audit trail method
                            auditins = Audittrail("ASSESSMENT", "ADD", None,
                                                  str(result[0]),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region

                            # region mail notification
                            notification_data = Notification.query.filter_by(
                                event_name="ASSESSMENTASSIGNMENT").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname, name=func_name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region
                    return make_response(jsonify({"msg": "Team Member successfully assigned.",
                                                  "data": result if len(result) > 1 else result[0]})), 201
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningteammember.route('/api/associateteammember/', methods=['PUT'])
def updateanddelete():
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
                row_id = res['row_id']
                data = Assessment.query.filter_by(id=row_id)
                projectid = data.first().projectid

                for user in data:
                    json_data = {'id': user.id, 'emp_id': user.emp_id,
                                 'project_id': user.projectid,
                                 'area_id': user.area_id,
                                 'functionality_id': user.functionality_id,
                                 'subfunctionality_id': user.subfunctionality_id,
                                 'employeeassignedstatus': user.employeeassignedstatus,
                                 'totalmaxscore': user.totalmaxscore,
                                 'totalscoreachieved': user.totalscoreachieved,
                                 'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                 'assessmenttakendatetime': user.assessmenttakendatetime,
                                 'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                 'active': user.active,
                                 'creationdatetime': user.creationdatetime,
                                 'updationdatetime': user.updationdatetime,
                                 'createdby': user.createdby,
                                 'modifiedby': user.modifiedby}
                    results.append(json_data)
                assessdatabefore = results[0]
                results.clear()

                if data.first() is None:
                    return make_response(jsonify({"msg": "Incorrect ID"})), 404
                else:
                    if request.method == 'PUT':
                        associate_status = res['associate_status']
                        if associate_status == 1:
                            data.first().employeeassignedstatus = 1
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()

                            data = Assessment.query.filter_by(id=row_id)
                            for user in data:
                                json_data = {'id': user.id, 'emp_id': user.emp_id,
                                             'project_id': user.projectid,
                                             'area_id': user.area_id,
                                             'functionality_id': user.functionality_id,
                                             'subfunctionality_id': user.subfunctionality_id,
                                             'employeeassignedstatus': user.employeeassignedstatus,
                                             'totalmaxscore': user.totalmaxscore,
                                             'totalscoreachieved': user.totalscoreachieved,
                                             'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                             'assessmenttakendatetime': user.assessmenttakendatetime,
                                             'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                             'active': user.active,
                                             'creationdatetime': user.creationdatetime,
                                             'updationdatetime': user.updationdatetime,
                                             'createdby': user.createdby,
                                             'modifiedby': user.modifiedby}
                                results.append(json_data)
                                managerdata = Projectassignmenttomanager.query.filter_by(project_id=projectid,
                                                                                         status=1).first()
                                if data.first() is not None:
                                    team_empid = data.first().emp_id
                                    userdata = Companyuserdetails.query.filter_by(empid=team_empid).first()
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
                                    subfunc_data = Subfunctionality.query.filter_by(
                                        id=user.subfunctionality_id)
                                    func_data = Functionality.query.filter_by(id=user.functionality_id)
                                    if subfunc_data.first() is not None:
                                        name = subfunc_data.first().name
                                    else:
                                        name = func_data.first().name
                                    # region mail notification
                                    notification_data = Notification.query.filter_by(
                                        event_name="ASSESSMENTASSOCIATIONTOTM").first()
                                    mail_subject = notification_data.mail_subject
                                    mail_body = str(notification_data.mail_body).\
                                        format(empname=empname, employeeassignedstatus="associated", name=name)
                                    mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname,
                                                           mail_body)
                                    print("======", mailout)
                                    # end region

                                    # triggering a mail to project manager
                                    userdata = Companyuserdetails.query.filter_by(empid=managerdata.emp_id).first()
                                    mailto = userdata.empemail
                                    mailtoname = userdata.empname
                                    # region mail notification
                                    notification_data = Notification.query.filter_by(
                                        event_name="ASSESSMENTASSOCIATIONTOMANAGER").first()
                                    mail_subject = notification_data.mail_subject
                                    mail_body = str(notification_data.mail_body).\
                                        format(managername=mailtoname, employeeassignedstatus="associated",
                                               empname=empname, name=name)
                                    mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname,
                                                           mail_body)
                                    print("======", mailout)
                                    # end region

                            assessdataafter = results[0]
                            # region call audit trail method
                            auditins = Audittrail("ASSESSMENT", "UPDATE", str(assessdatabefore), str(assessdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            return make_response(jsonify({"msg": "Team Member associated successfully "})), 200
                        else:
                            data.first().employeeassignedstatus = 0
                            data.first().modifiedby = session['empid']
                            db.session.add(data.first())
                            db.session.commit()

                            data = Assessment.query.filter_by(id=row_id)
                            for user in data:
                                json_data = {'id': user.id, 'emp_id': user.emp_id,
                                             'project_id': user.projectid,
                                             'area_id': user.area_id,
                                             'functionality_id': user.functionality_id,
                                             'subfunctionality_id': user.subfunctionality_id,
                                             'employeeassignedstatus': user.employeeassignedstatus,
                                             'totalmaxscore': user.totalmaxscore,
                                             'totalscoreachieved': user.totalscoreachieved,
                                             'comment': user.comment, 'assessmentstatus': user.assessmentstatus,
                                             'assessmenttakendatetime': user.assessmenttakendatetime,
                                             'assessmentrevieweddatetime': user.assessmentrevieweddatetime,
                                             'active': user.active,
                                             'creationdatetime': user.creationdatetime,
                                             'updationdatetime': user.updationdatetime,
                                             'createdby': user.createdby,
                                             'modifiedby': user.modifiedby}
                                results.append(json_data)
                                managerdata = Projectassignmenttomanager.query.filter_by(project_id=projectid,
                                                                                         status=1).first()
                                if data.first() is not None:
                                    team_empid = data.first().emp_id
                                    userdata = Companyuserdetails.query.filter_by(empid=team_empid).first()
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

                                    subfunc_data = Subfunctionality.query.filter_by(
                                        id=user.subfunctionality_id)
                                    func_data = Functionality.query.filter_by(id=user.functionality_id)
                                    if subfunc_data.first() is not None:
                                        name = subfunc_data.first().name
                                    else:
                                        name = func_data.first().name

                                    # region mail notification
                                    notification_data = Notification.query.filter_by(
                                        event_name="ASSESSMENTASSOCIATIONTOTM").first()
                                    mail_subject = notification_data.mail_subject
                                    mail_body = str(notification_data.mail_body).\
                                        format(empname=empname, employeeassignedstatus="disassociated", name=name)
                                    mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname,
                                                           mail_body)
                                    print("======", mailout)
                                    # end region

                                    # triggering a mail to project manager
                                    userdata = Companyuserdetails.query.filter_by(empid=managerdata.emp_id).first()
                                    mailto = userdata.empemail
                                    mailtoname = userdata.empname
                                    # region mail notification
                                    notification_data = Notification.query.filter_by(
                                        event_name="ASSESSMENTASSOCIATIONTOMANAGER").first()
                                    mail_subject = notification_data.mail_subject
                                    mail_body = str(notification_data.mail_body).\
                                        format(managername=mailtoname, employeeassignedstatus="disassociated",
                                               empname=empname, name=name)
                                    mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname,
                                                           mail_body)
                                    print("======", mailout)
                                    # end region

                            assessdataafter = results[0]
                            # region call audit trail method
                            auditins = Audittrail("ASSESSMENT", "UPDATE", str(assessdatabefore), str(assessdataafter),
                                                  session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            return make_response(jsonify({"msg": "Team Member disassociated successfully"})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningteammember.route('/api/fetchprojectassigntoteam/', methods=['POST'])
def fetchprojectassigntoteam():
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
                    data = Assessment.query.distinct(Assessment.projectid).filter(Assessment.emp_id == emp_id,
                                                                                  Assessment.
                                                                                  employeeassignedstatus == 1)
                    lists = []
                    for user in data:
                        project_data = Project.query.filter(Project.id == user.projectid)
                        if project_data.first() is not None:
                            lists.append({'projectid': user.projectid, 'projectname': project_data.first().name,
                                          'needforreview': project_data.first().needforreview})
                    return make_response(jsonify({"data": lists})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401

        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningteammember.route('/api/fetchareanametoteam/', methods=['POST'])
def fetchareanametoteam():
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
                    projectid = res['projectid']
                    data = Assessment.query.distinct(Assessment.area_id).filter(Assessment.emp_id == emp_id,
                                                                                Assessment.projectid == projectid,
                                                                                Assessment.employeeassignedstatus == 1)

                    lists = []
                    for user in data:
                        area_data = Area.query.filter(Area.id == user.area_id)
                        if area_data.first() is not None:
                            lists.append({'area_id': user.area_id, 'area_name': area_data.first().name})
                    return make_response(jsonify({"data": lists})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401

        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningteammember.route('/api/fetchfunctionalitynametoteam/', methods=['POST'])
def fetchfunctionalitynametoteam():
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
                    projectid = res['projectid']
                    area_id = res['area_id']
                    data = Assessment.query.distinct(Assessment.functionality_id).\
                        filter(Assessment.emp_id == emp_id, Assessment.projectid == projectid,
                               Assessment.area_id == area_id, Assessment.employeeassignedstatus == 1)
                    lists = []
                    for user in data:
                        functionality_data = Functionality.query.filter(
                            Functionality.id == user.functionality_id)
                        if functionality_data.first() is not None:
                            lists.append(
                                {'functionality_id': user.functionality_id,
                                 'functionality_name': functionality_data.first().name})
                    return make_response(jsonify({"data": lists})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401

        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@assigningteammember.route('/api/fetchSubfunctionalitynametoteam/', methods=['POST'])
def fetchsubfunctionalitynametoteam():
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
                    projectid = res['projectid']
                    area_id = res['area_id']
                    functionality_id = res['functionality_id']
                    data = Assessment.query.distinct(Assessment.subfunctionality_id).\
                        filter(Assessment.emp_id == emp_id, Assessment.projectid == projectid,
                               Assessment.area_id == area_id, Assessment.functionality_id == functionality_id,
                               Assessment.employeeassignedstatus == 1)
                    lists = []
                    for user in data:
                        if user.subfunctionality_id is not None:
                            subfunc_data = Subfunctionality.query.filter(
                                Subfunctionality.id == user.subfunctionality_id)
                            if subfunc_data.first() is not None:
                                lists.append({'sucfunc_id': user.subfunctionality_id,
                                              'subfunc_name': subfunc_data.first().name})
                        else:
                            pass
                    return make_response(jsonify({"data": lists})), 200
            else:
                return make_response(jsonify({"msg": resp})), 401

        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
