import os
import base64
import xlrd
from flask import request, make_response, session, Blueprint, jsonify
from DOEAssessmentApp import app, db
from DOEAssessmentApp.DOE_models.project_model import Project
from DOEAssessmentApp.DOE_models.area_model import Area
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.question_model import Question
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.email_configuration_model import Emailconfiguration
from DOEAssessmentApp.DOE_models.project_assignment_to_manager_model import Projectassignmenttomanager
from DOEAssessmentApp.DOE_models.company_details_model import Companydetails
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail
from DOEAssessmentApp.DOE_models.notification_model import Notification
from DOEAssessmentApp.smtp_integration import trigger_mail

project = Blueprint('project', __name__)

cols_subfunc = ['id', 'name', 'description', 'retake_assessment_days', 'func_id', 'area_id', 'proj_id',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']

colsquestion = ['id', 'name', 'answer_type', 'answers', 'maxscore', 'subfunc_id', 'func_id', 'area_id', 'proj_id',
                'combination', 'mandatory', 'islocked', 'isdependentquestion',
                'creationdatetime', 'updationdatetime', 'createdby', 'modifiedby']


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@project.route('/api/project', methods=['GET', 'POST'])
def getaddproject():
    """
        ---
        get:
          description: Fetch project(s).
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
              - getcreateproject
        post:
          description: Create a project.
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
              - getcreateproject
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
                    data = Project.query.all()
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'levels': d.levels},
                                              {'companyid': d.companyid},
                                              {'achievedlevel': d.achievedlevel},
                                              {'needforreview': d.needforreview},
                                              {'assessmentcompletion': str(d.assessmentcompletion)},
                                              {'achievedpercentage': str(d.achievedpercentage)},
                                              {'creationdatetime': d.creationdatetime},
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime})
                        results.append(json_data)
                    return make_response(jsonify({"data": results})), 200
                elif request.method == "POST":
                    count_of_project = Project.query.all().count()
                    if count_of_project < app.config.get('NOOFPROJECTS'):
                        res = request.get_json(force=True)
                        if 'excelfordefaultquestions' in res:
                            excelfordefaultquestions = res['excelfordefaultquestions']
                        else:
                            excelfordefaultquestions = None
                        projname = res['name']
                        projdesc = res['description']
                        comp_id = res['companyid']
                        levels = res['levels']
                        if 'needforreview' in res:
                            nfr = res['needforreview']
                        else:
                            nfr = 1
                        existing_project = Project.query.filter(Project.name == projname,
                                                                Project.companyid == comp_id).one_or_none()
                        if existing_project is None:
                            projins = Project(projname, projdesc, levels, comp_id, nfr, session['empid'])
                            db.session.add(projins)
                            db.session.commit()
                            session["projid"] = projins.id
                            data = Project.query.filter_by(id=projins.id)
                            for d in data:
                                json_data = mergedict({'id': d.id},
                                                      {'name': d.name},
                                                      {'description': d.description},
                                                      {'levels': d.levels},
                                                      {'companyid': d.companyid},
                                                      {'achievedlevel': d.achievedlevel},
                                                      {'needforreview': d.needforreview},
                                                      {'assessmentcompletion': str(d.assessmentcompletion)},
                                                      {'achievedpercentage': str(d.achievedpercentage)},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                      {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                results.append(json_data)
                            newaddedproject = results[0]
                            # region call audit trail method
                            auditins = Audittrail("PROJECT", "ADD", None, str(results[0]), session['empid'])
                            db.session.add(auditins)
                            db.session.commit()
                            # end region
                            if excelfordefaultquestions is not None:
                                wb = xlrd.open_workbook('static/' + excelfordefaultquestions + '.xlsx')
                                sh = wb.sheet_by_name('Sheet2')
                                for i in range(1, sh.nrows):
                                    existing_area = Area.query.filter(Area.name == sh.cell_value(i, 0),
                                                                      Area.projectid == projins.id).one_or_none()
                                    if existing_area is None:
                                        areains = Area(sh.cell_value(i, 0), sh.cell_value(i, 1), projins.id,
                                                       session['empid'])
                                        db.session.add(areains)
                                        db.session.commit()
                                        data = Area.query.filter_by(id=areains.id)
                                        for d in data:
                                            json_data = mergedict({'id': d.id},
                                                                  {'name': d.name},
                                                                  {'description': d.description},
                                                                  {'projectid': d.projectid},
                                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                                  {'achievedlevel': d.achievedlevel},
                                                                  {'creationdatetime': d.creationdatetime},
                                                                  {'prevassessmentcompletion': str(
                                                                      d.prevassessmentcompletion)},
                                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                                  {'updationdatetime': d.updationdatetime},
                                                                  {'createdby': d.createdby},
                                                                  {'modifiedby': d.modifiedby})
                                            results.append(json_data)
                                        # region call audit trail method
                                        auditins = Audittrail("AREA", "ADD", None, str(results[0]),
                                                              session['empid'])
                                        db.session.add(auditins)
                                        db.session.commit()
                                        # end region
                                    findareadata = Area.query.filter_by(name=sh.cell_value(i, 0),
                                                                        projectid=projins.id).first()
                                    existing_functionality = Functionality.query.filter(
                                        Functionality.name == sh.cell_value(i, 2),
                                        Functionality.area_id ==
                                        findareadata.id).one_or_none()
                                    if existing_functionality is None:
                                        funcins = Functionality(sh.cell_value(i, 2),
                                                                sh.cell_value(i, 3),
                                                                sh.cell_value(i, 7) if sh.cell_value(i, 5) == '' else None,
                                                                findareadata.id, projins.id, session['empid'],
                                                                1 if sh.cell_value(i, 4) == 'Very High' else
                                        2 if sh.cell_value(i, 4) == 'High' else 3 if sh.cell_value(i, 4) == 'Medium' else
                                        4 if sh.cell_value(i, 4) == 'Low' else 5 if sh.cell_value(i, 4) == 'Very Low' else
                                                                None)
                                        db.session.add(funcins)
                                        db.session.commit()
                                        data = Functionality.query.filter_by(id=funcins.id)
                                        for d in data:
                                            json_data = mergedict({'id': d.id},
                                                                  {'name': d.name},
                                                                  {'description': d.description},
                                                                  {'retake_assessment_days': d.retake_assessment_days},
                                                                  {'area_id': d.area_id},
                                                                  {'proj_id': d.proj_id},
                                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                                  {'achievedlevel': d.achievedlevel},
                                                                  {'creationdatetime': d.creationdatetime},
                                                                  {'prevassessmentcompletion': str(
                                                                      d.prevassessmentcompletion)},
                                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                                  {'updationdatetime': d.updationdatetime},
                                                                  {'createdby': d.createdby},
                                                                  {'modifiedby': d.modifiedby})
                                            results.append(json_data)
                                        # region call audit trail method
                                        auditins = Audittrail("FUNCTIONALITY", "ADD", None, str(results[0]),
                                                              session['empid'])
                                        db.session.add(auditins)
                                        db.session.commit()
                                        # end region
                                    if sh.cell_value(i, 5) != '':
                                        findfuncdata = Functionality.query.filter_by(
                                            name=sh.cell_value(i, 2),
                                            area_id=findareadata.id).first()
                                        existing_subfunctionality = Subfunctionality.query.filter(
                                            Subfunctionality.name ==
                                            sh.cell_value(i, 5),
                                            Subfunctionality.func_id ==
                                            findfuncdata.id).one_or_none()
                                        if existing_subfunctionality is None:
                                            subfuncins = Subfunctionality(sh.cell_value(i, 4),
                                                                          sh.cell_value(i, 6),
                                                                          sh.cell_value(i, 7),
                                                                          findfuncdata.id, findareadata.id, projins.id,
                                                                          session['empid'])
                                            db.session.add(subfuncins)
                                            db.session.commit()
                                            data = Subfunctionality.query.filter_by(id=subfuncins.id)
                                            results = [{col: getattr(d, col) for col in cols_subfunc} for d in data]
                                            # region call audit trail method
                                            auditins = Audittrail("SUB-FUNCTIONALITY", "ADD", None, str(results[0]),
                                                                  session['empid'])
                                            db.session.add(auditins)
                                            db.session.commit()
                                            # end region
                                            # add question in new sub func
                                            combination = str(projins.id) + str(findareadata.id) + str(
                                                findfuncdata.id) + str(subfuncins.id) + str(sh.cell_value(i, 8))
                                            existing_question = Question.query.filter(
                                                Question.combination == combination).one_or_none()
                                            if existing_question is None:
                                                maxscore = 0
                                                answers = []
                                                if sh.cell_value(i, 10) == 'Yes / No':
                                                    answers = [
                                                        {
                                                            "option1": sh.cell_value(i, 11),
                                                            "score": sh.cell_value(i, 12),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + child).first().id for child in
                                                                sh.cell_value(i, 13).split(',') if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        subfuncins.id) + child) is not None] if ',' in sh.
                                                                cell_value(i, 13)
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(findareadata.id) + str(
                                                                    findfuncdata.id) + str(subfuncins.id) +
                                                                            sh.cell_value(i, 13)) is None else
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(findareadata.id) + str(
                                                                    findfuncdata.id) + str(subfuncins.id) +
                                                                            sh.cell_value(i, 13)).first().id
                                                            if sh.cell_value(i, 13) != ''
                                                            else 0
                                                        },
                                                        {
                                                            "option2": sh.cell_value(i, 14),
                                                            "score": sh.cell_value(i, 15),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + child).first().id for child in
                                                                sh.cell_value(i, 16).split(',') if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        subfuncins.id) + child) is not None] if ',' in sh.
                                                                cell_value(i, 16)
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + sh.cell_value(i, 16)) is None else
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                subfuncins.id) + sh.cell_value(i, 16)).first().id
                                                            if sh.cell_value(i, 16) != ''
                                                            else 0
                                                        }
                                                    ]
                                                    maxscore = max(int(sh.cell_value(i, 12)), int(sh.cell_value(i, 15)))
                                                elif sh.cell_value(i, 10) == 'Multi choice':
                                                    k = 1
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): sh.cell_value(i, j),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child).first().id for
                                                                        child in
                                                                        sh.cell_value(i, j + 2).split(',') if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child) is
                                                                        not None] if ',' in sh.cell_value(
                                                                        i, j + 2)
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + sh.
                                                                                        cell_value(i, j + 2)) is None else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + sh.
                                                                                        cell_value(i, j + 2)).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            maxscore = maxscore + int(sh.cell_value(i, j + 1))
                                                            k = k + 1
                                                        else:
                                                            break
                                                elif sh.cell_value(i, 10) == 'Single choice':
                                                    k = 1
                                                    scores = []
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): sh.cell_value(i, j),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child).first().id for
                                                                        child in
                                                                        sh.cell_value(i, j + 2).split(',') if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child) is
                                                                        not None] if ',' in sh.cell_value(
                                                                        i, j + 2)
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + sh.
                                                                                        cell_value(i, j + 2)) is None else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + sh.
                                                                                        cell_value(i, j + 2)).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            scores.append(int(sh.cell_value(i, j + 1)))
                                                            k = k + 1
                                                        else:
                                                            break
                                                        maxscore = max(scores)
                                                quesins = Question(sh.cell_value(i, 8), sh.cell_value(i, 10), answers,
                                                                   maxscore,
                                                                   subfuncins.id,
                                                                   findfuncdata.id, findareadata.id, projins.id,
                                                                   combination, sh.cell_value(i, 9), session['empid'])
                                                db.session.add(quesins)
                                                db.session.commit()
                                                for a in answers:
                                                    if a['childquestionid'] != 0:
                                                        if isinstance(a['childquestionid'], list):
                                                            for c in a['childquestionid']:
                                                                data = Question.query.filter_by(id=c)
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d
                                                                          in data]
                                                                quesdatabefore = result[0]
                                                                result.clear()
                                                                if data.first() is not None:
                                                                    data.first().isdependentquestion = 1
                                                                    data.first().modifiedby = session['empid']
                                                                    data.first().islocked = 0
                                                                    db.session.add(data.first())
                                                                    db.session.commit()
                                                                    data = Question.query.filter_by(id=c)
                                                                    result = [{col: getattr(d, col) for col in colsquestion}
                                                                              for
                                                                              d in data]
                                                                    quesdataafter = result[0]
                                                                    result.clear()
                                                                    # region call audit trail method
                                                                    auditins = Audittrail("QUESTION", "UPDATE",
                                                                                          str(quesdatabefore),
                                                                                          str(quesdataafter),
                                                                                          session['empid'])
                                                                    db.session.add(auditins)
                                                                    db.session.commit()
                                                                    # end region
                                                        else:
                                                            data = Question.query.filter_by(id=a['childquestionid'])
                                                            result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                      in data]
                                                            quesdatabefore = result[0]
                                                            result.clear()
                                                            if data.first() is not None:
                                                                data.first().isdependentquestion = 1
                                                                data.first().modifiedby = session['empid']
                                                                data.first().islocked = 0
                                                                db.session.add(data.first())
                                                                db.session.commit()
                                                                data = Question.query.filter_by(id=a['childquestionid'])
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d in data]
                                                                quesdataafter = result[0]
                                                                result.clear()
                                                                # region call audit trail method
                                                                auditins = Audittrail("QUESTION", "UPDATE",
                                                                                      str(quesdatabefore),
                                                                                      str(quesdataafter),
                                                                                      session['empid'])
                                                                db.session.add(auditins)
                                                                db.session.commit()
                                                                # end region
                                                data = Question.query.filter_by(id=quesins.id)
                                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                                # region call audit trail method
                                                auditins = Audittrail("QUESTION", "ADD", None, str(results[0]),
                                                                      session['empid'])
                                                db.session.add(auditins)
                                                db.session.commit()
                                                # end region
                                            else:
                                                pass
                                        else:
                                            # add questions in sub func which already exists
                                            findsubfuncdata = Subfunctionality.query.filter(Subfunctionality.name ==
                                                                                            sh.cell_value(i, 5),
                                                                                            Subfunctionality.func_id ==
                                                                                            findfuncdata.id).one_or_none()
                                            combination = str(projins.id) + str(findareadata.id) + str(
                                                findfuncdata.id) + str(findsubfuncdata.id) + str(sh.cell_value(i, 8))
                                            existing_question = Question.query.filter(
                                                Question.combination == combination).one_or_none()
                                            if existing_question is None:
                                                maxscore = 0
                                                answers = []
                                                if sh.cell_value(i, 10) == 'Yes / No':
                                                    answers = [
                                                        {
                                                            "option1": sh.cell_value(i, 11),
                                                            "score": sh.cell_value(i, 12),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + child).first().id for child in
                                                                sh.cell_value(i, 13).split(',') if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        findsubfuncdata.id) + child) is not None] if ',' in sh.
                                                                cell_value(i, 13)
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + sh.cell_value(i, 13)) is None else
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                findsubfuncdata.id) + sh.cell_value(i, 13)).first().id
                                                            if sh.cell_value(i, 13) != ''
                                                            else 0
                                                        },
                                                        {
                                                            "option2": sh.cell_value(i, 14),
                                                            "score": sh.cell_value(i, 15),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + child).first().id for child in
                                                                sh.cell_value(i, 16).split(',') if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        findsubfuncdata.id) + child) is not None] if ',' in sh.
                                                                cell_value(i, 16)
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + sh.cell_value(i, 16)) is None else
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                findsubfuncdata.id) + sh.cell_value(i, 16)).first().id
                                                            if sh.cell_value(i, 16) != ''
                                                            else 0
                                                        }
                                                    ]
                                                    maxscore = max(int(sh.cell_value(i, 12)), int(sh.cell_value(i, 15)))
                                                elif sh.cell_value(i, 10) == 'Multi choice':
                                                    k = 1
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): sh.cell_value(i, j),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child).first().id for
                                                                        child in
                                                                        sh.cell_value(i, j + 2).split(',') if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child) is
                                                                        not None] if ',' in sh.cell_value(
                                                                        i, j + 2)
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) + sh.
                                                                                        cell_value(i, j + 2)) is None else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) + sh.
                                                                                        cell_value(i, j + 2)).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            maxscore = maxscore + int(sh.cell_value(i, j + 1))
                                                            k = k + 1
                                                        else:
                                                            break
                                                elif sh.cell_value(i, 10) == 'Single choice':
                                                    k = 1
                                                    scores = []
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): sh.cell_value(i, j),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child).first().id for
                                                                        child in
                                                                        sh.cell_value(i, j + 2).split(',') if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child) is
                                                                        not None] if ',' in sh.cell_value(
                                                                        i, j + 2)
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) + sh.
                                                                                        cell_value(i, j + 2)) is None else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) + sh.
                                                                                        cell_value(i, j + 2)).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            scores.append(int(sh.cell_value(i, j + 1)))
                                                            k = k + 1
                                                        else:
                                                            break
                                                        maxscore = max(scores)
                                                quesins = Question(sh.cell_value(i, 8), sh.cell_value(i, 10), answers,
                                                                   maxscore,
                                                                   findsubfuncdata.id,
                                                                   findfuncdata.id, findareadata.id, projins.id,
                                                                   combination, sh.cell_value(i, 9), session['empid'])
                                                db.session.add(quesins)
                                                db.session.commit()
                                                for a in answers:
                                                    if a['childquestionid'] != 0:
                                                        if isinstance(a['childquestionid'], list):
                                                            for c in a['childquestionid']:
                                                                data = Question.query.filter_by(id=c)
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d
                                                                          in data]
                                                                quesdatabefore = result[0]
                                                                result.clear()
                                                                if data.first() is not None:
                                                                    data.first().isdependentquestion = 1
                                                                    data.first().modifiedby = session['empid']
                                                                    data.first().islocked = 0
                                                                    db.session.add(data.first())
                                                                    db.session.commit()
                                                                    data = Question.query.filter_by(id=c)
                                                                    result = [{col: getattr(d, col) for col in colsquestion}
                                                                              for
                                                                              d in data]
                                                                    quesdataafter = result[0]
                                                                    result.clear()
                                                                    # region call audit trail method
                                                                    auditins = Audittrail("QUESTION", "UPDATE",
                                                                                          str(quesdatabefore),
                                                                                          str(quesdataafter),
                                                                                          session['empid'])
                                                                    db.session.add(auditins)
                                                                    db.session.commit()
                                                                    # end region
                                                        else:
                                                            data = Question.query.filter_by(id=a['childquestionid'])
                                                            result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                      in data]
                                                            quesdatabefore = result[0]
                                                            result.clear()
                                                            if data.first() is not None:
                                                                data.first().isdependentquestion = 1
                                                                data.first().modifiedby = session['empid']
                                                                data.first().islocked = 0
                                                                db.session.add(data.first())
                                                                db.session.commit()
                                                                data = Question.query.filter_by(id=a['childquestionid'])
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d in data]
                                                                quesdataafter = result[0]
                                                                result.clear()
                                                                # region call audit trail method
                                                                auditins = Audittrail("QUESTION", "UPDATE",
                                                                                      str(quesdatabefore),
                                                                                      str(quesdataafter),
                                                                                      session['empid'])
                                                                db.session.add(auditins)
                                                                db.session.commit()
                                                                # end region
                                                data = Question.query.filter_by(id=quesins.id)
                                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                                # region call audit trail method
                                                auditins = Audittrail("QUESTION", "ADD", None, str(results[0]),
                                                                      session['empid'])
                                                db.session.add(auditins)
                                                db.session.commit()
                                                # end region
                                            else:
                                                pass
                                    else:
                                        # add questions in func when subfunc does not exists for this func
                                        findfuncdata = Functionality.query.filter_by(
                                            name=sh.cell_value(i, 2),
                                            area_id=findareadata.id).first()
                                        combination = str(projins.id) + str(findareadata.id) + str(
                                            findfuncdata.id) + str(sh.cell_value(i, 8))
                                        existing_question = Question.query.filter(
                                            Question.combination == combination).one_or_none()
                                        if existing_question is None:
                                            maxscore = 0
                                            answers = []
                                            if sh.cell_value(i, 10) == 'Yes / No':
                                                answers = [
                                                    {
                                                        "option1": sh.cell_value(i, 11),
                                                        "score": sh.cell_value(i, 12),
                                                        "childquestionid": [
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + child).first().id for child in
                                                            sh.cell_value(i, 13).split(',') if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + child) is not None] if ',' in sh.
                                                            cell_value(i, 13)
                                                        else 0 if Question.query.filter_by(
                                                            combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + sh.cell_value(i, 13)) is None else
                                                        Question.query.filter_by(combination=str(projins.id) + str(
                                                            findareadata.id) + str(
                                                            findfuncdata.id) + sh.cell_value(i, 13)).first().id
                                                        if sh.cell_value(i, 13) != ''
                                                        else 0
                                                    },
                                                    {
                                                        "option2": sh.cell_value(i, 14),
                                                        "score": sh.cell_value(i, 15),
                                                        "childquestionid": [
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + child).first().id for child in
                                                            sh.cell_value(i, 16).split(',') if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + child) is not None] if ',' in sh.
                                                            cell_value(i, 16)
                                                        else 0 if Question.query.filter_by(
                                                            combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + sh.cell_value(i, 16)) is None else
                                                        Question.query.filter_by(combination=str(projins.id) + str(
                                                            findareadata.id) + str(
                                                            findfuncdata.id) + sh.cell_value(i, 16)).first().id
                                                        if sh.cell_value(i, 16) != ''
                                                        else 0
                                                    }
                                                ]
                                                maxscore = max(int(sh.cell_value(i, 12)), int(sh.cell_value(i, 15)))
                                            elif sh.cell_value(i, 10) == 'Multi choice':
                                                k = 1
                                                for j in range(11, sh.ncols, 3):
                                                    if sh.cell_value(i, j) != '':
                                                        answers.append(
                                                            {
                                                                "option{0}".format(k): sh.cell_value(i, j),
                                                                "score": sh.cell_value(i, j + 1),
                                                                "childquestionid": [
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child).first().id for
                                                                    child in
                                                                    sh.cell_value(i, j + 2).split(',') if
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child) is
                                                                    not None] if ',' in sh.cell_value(
                                                                    i, j + 2)
                                                                else 0 if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + sh.
                                                                                    cell_value(i, j + 2)) is None else
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + sh.
                                                                                    cell_value(i, j + 2)).first().id
                                                                if sh.cell_value(i, j + 2) != ''
                                                                else 0
                                                            })
                                                        maxscore = maxscore + int(sh.cell_value(i, j + 1))
                                                        k = k + 1
                                                    else:
                                                        break
                                            elif sh.cell_value(i, 10) == 'Single choice':
                                                k = 1
                                                scores = []
                                                for j in range(11, sh.ncols, 3):
                                                    if sh.cell_value(i, j) != '':
                                                        answers.append(
                                                            {
                                                                "option{0}".format(k): sh.cell_value(i, j),
                                                                "score": sh.cell_value(i, j + 1),
                                                                "childquestionid": [
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child).first().id for
                                                                    child in
                                                                    sh.cell_value(i, j + 2).split(',') if
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child) is
                                                                    not None] if ',' in sh.cell_value(
                                                                    i, j + 2)
                                                                else 0 if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + sh.
                                                                                    cell_value(i, j + 2)) is None else
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + sh.
                                                                                    cell_value(i, j + 2)).first().id
                                                                if sh.cell_value(i, j + 2) != ''
                                                                else 0
                                                            })
                                                        scores.append(int(sh.cell_value(i, j + 1)))
                                                        k = k + 1
                                                    else:
                                                        break
                                                    maxscore = max(scores)
                                            quesins = Question(sh.cell_value(i, 8), sh.cell_value(i, 10), answers,
                                                               maxscore,
                                                               None,
                                                               findfuncdata.id, findareadata.id, projins.id,
                                                               combination, sh.cell_value(i, 9), session['empid'])
                                            db.session.add(quesins)
                                            db.session.commit()
                                            for a in answers:
                                                if a['childquestionid'] != 0:
                                                    if isinstance(a['childquestionid'], list):
                                                        for c in a['childquestionid']:
                                                            data = Question.query.filter_by(id=c)
                                                            result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                      in data]
                                                            quesdatabefore = result[0]
                                                            result.clear()
                                                            if data.first() is not None:
                                                                data.first().isdependentquestion = 1
                                                                data.first().modifiedby = session['empid']
                                                                data.first().islocked = 0
                                                                db.session.add(data.first())
                                                                db.session.commit()
                                                                data = Question.query.filter_by(id=c)
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d in data]
                                                                quesdataafter = result[0]
                                                                result.clear()
                                                                # region call audit trail method
                                                                auditins = Audittrail("QUESTION", "UPDATE",
                                                                                      str(quesdatabefore),
                                                                                      str(quesdataafter),
                                                                                      session['empid'])
                                                                db.session.add(auditins)
                                                                db.session.commit()
                                                                # end region
                                                    else:
                                                        data = Question.query.filter_by(id=a['childquestionid'])
                                                        result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                  in data]
                                                        quesdatabefore = result[0]
                                                        result.clear()
                                                        if data.first() is not None:
                                                            data.first().isdependentquestion = 1
                                                            data.first().modifiedby = session['empid']
                                                            data.first().islocked = 0
                                                            db.session.add(data.first())
                                                            db.session.commit()
                                                            data = Question.query.filter_by(id=a['childquestionid'])
                                                            result = [{col: getattr(d, col) for col in colsquestion} for
                                                                      d in data]
                                                            quesdataafter = result[0]
                                                            result.clear()
                                                            # region call audit trail method
                                                            auditins = Audittrail("QUESTION", "UPDATE",
                                                                                  str(quesdatabefore),
                                                                                  str(quesdataafter),
                                                                                  session['empid'])
                                                            db.session.add(auditins)
                                                            db.session.commit()
                                                            # end region
                                            data = Question.query.filter_by(id=quesins.id)
                                            results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                            # region call audit trail method
                                            auditins = Audittrail("QUESTION", "ADD", None, str(results[0]),
                                                                  session['empid'])
                                            db.session.add(auditins)
                                            db.session.commit()
                                            # end region
                                        else:
                                            pass
                                return make_response(jsonify({"message": f"Project {projname} has been successfully "
                                                                         f"added with "
                                                                         f"default assessments.",
                                                              "data": newaddedproject})), 201
                            elif 'udquesfilebase64' in res and 'filename' in res:
                                xldecoded = base64.b64decode(res['udquesfilebase64'])
                                xlfile = open(os.path.join('static/', res['filename']), 'wb')
                                xlfile.write(xldecoded)
                                xlfile.close()
                                wb = xlrd.open_workbook('static/' + res['filename'])
                                sh = wb.sheet_by_name('Sheet2')
                                for i in range(1, sh.nrows):
                                    existing_area = Area.query.filter(Area.name == str(sh.cell_value(i, 0)).strip(),
                                                                      Area.projectid == projins.id).one_or_none()
                                    if existing_area is None:
                                        areains = Area(str(sh.cell_value(i, 0)).strip(),
                                                       str(sh.cell_value(i, 1)).strip(), projins.id, session['empid'])
                                        db.session.add(areains)
                                        db.session.commit()
                                        data = Area.query.filter_by(id=areains.id)
                                        for d in data:
                                            json_data = mergedict({'id': d.id},
                                                                  {'name': d.name},
                                                                  {'description': d.description},
                                                                  {'projectid': d.projectid},
                                                                  {'assessmentcompletion': str(
                                                                      d.assessmentcompletion)},
                                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                                  {'achievedlevel': d.achievedlevel},
                                                                  {'creationdatetime': d.creationdatetime},
                                                                  {'prevassessmentcompletion': str(
                                                                      d.prevassessmentcompletion)},
                                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                                  {'updationdatetime': d.updationdatetime},
                                                                  {'createdby': d.createdby},
                                                                  {'modifiedby': d.modifiedby})
                                            results.append(json_data)
                                        # region call audit trail method
                                        auditins = Audittrail("AREA", "ADD", None, str(results[0]),
                                                              session['empid'])
                                        db.session.add(auditins)
                                        db.session.commit()
                                        # end region
                                    findareadata = Area.query.filter_by(name=str(sh.cell_value(i, 0)).strip(),
                                                                        projectid=projins.id).first()
                                    existing_functionality = Functionality.query.filter(
                                        Functionality.name == str(sh.cell_value(i, 2)).strip(),
                                        Functionality.area_id ==
                                        findareadata.id).one_or_none()
                                    if existing_functionality is None:
                                        funcins = Functionality(str(sh.cell_value(i, 2)).strip(),
                                                                str(sh.cell_value(i, 3)).strip(),
                                                                sh.cell_value(i, 7)
                                                                if str(sh.cell_value(i, 5)).strip() == '' else None,
                                                                findareadata.id, projins.id, session['empid'],
                                                                1 if sh.cell_value(i, 4) == 'Very High' else
                                                                2 if sh.cell_value(i, 4) == 'High' else 3 if sh.cell_value(
                                                                    i, 4) == 'Medium' else
                                                                4 if sh.cell_value(i, 4) == 'Low' else
                                                                5 if sh.cell_value(i, 4) == 'Very Low' else
                                                                None)
                                        db.session.add(funcins)
                                        db.session.commit()
                                        data = Functionality.query.filter_by(id=funcins.id)
                                        for d in data:
                                            json_data = mergedict({'id': d.id},
                                                                  {'name': d.name},
                                                                  {'description': d.description},
                                                                  {'retake_assessment_days':
                                                                       d.retake_assessment_days},
                                                                  {'area_id': d.area_id},
                                                                  {'proj_id': d.proj_id},
                                                                  {'assessmentcompletion': str(
                                                                      d.assessmentcompletion)},
                                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                                  {'achievedlevel': d.achievedlevel},
                                                                  {'creationdatetime': d.creationdatetime},
                                                                  {'prevassessmentcompletion': str(
                                                                      d.prevassessmentcompletion)},
                                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                                  {'updationdatetime': d.updationdatetime},
                                                                  {'createdby': d.createdby},
                                                                  {'modifiedby': d.modifiedby})
                                            results.append(json_data)
                                        # region call audit trail method
                                        auditins = Audittrail("FUNCTIONALITY", "ADD", None, str(results[0]),
                                                              session['empid'])
                                        db.session.add(auditins)
                                        db.session.commit()
                                        # end region
                                    if sh.cell_value(i, 5) != '':
                                        findfuncdata = Functionality.query.filter_by(
                                            name=str(sh.cell_value(i, 2)).strip(),
                                            area_id=findareadata.id).first()
                                        existing_subfunctionality = Subfunctionality.query.filter(
                                            Subfunctionality.name ==
                                            str(sh.cell_value(i, 5)).strip(),
                                            Subfunctionality.func_id ==
                                            findfuncdata.id).one_or_none()
                                        if existing_subfunctionality is None:
                                            subfuncins = Subfunctionality(str(sh.cell_value(i, 5)).strip(),
                                                                          str(sh.cell_value(i, 6)).strip(),
                                                                          sh.cell_value(i, 7),
                                                                          findfuncdata.id, findareadata.id,
                                                                          projins.id, session['empid'])
                                            db.session.add(subfuncins)
                                            db.session.commit()
                                            data = Subfunctionality.query.filter_by(id=subfuncins.id)
                                            results = [{col: getattr(d, col) for col in cols_subfunc} for d in data]
                                            # region call audit trail method
                                            auditins = Audittrail("SUB-FUNCTIONALITY", "ADD", None, str(results[0]),
                                                                  session['empid'])
                                            db.session.add(auditins)
                                            db.session.commit()
                                            # end region
                                            # add question in new sub func
                                            combination = str(projins.id) + str(findareadata.id) + str(
                                                findfuncdata.id) + str(subfuncins.id) + str(
                                                sh.cell_value(i, 8)).strip()
                                            existing_question = Question.query.filter(
                                                Question.combination == combination).one_or_none()
                                            if existing_question is None:
                                                maxscore = 0
                                                answers = []
                                                if str(sh.cell_value(i, 10)).strip() == 'Yes / No':
                                                    answers = [
                                                        {
                                                            "option1": str(sh.cell_value(i, 11)).strip(),
                                                            "score": sh.cell_value(i, 12),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + child).first().id for
                                                                child in
                                                                str(sh.cell_value(i, 13)).strip().split(',') if
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        subfuncins.id) + child) is not None] if ',' in str(
                                                                sh.cell_value(i,
                                                                              13)).strip()
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + str(
                                                                    sh.cell_value(i, 13)).strip()) is None else
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + str(
                                                                    sh.cell_value(i, 13)).strip()).first().id
                                                            if sh.cell_value(i, 13) != ''
                                                            else 0
                                                        },
                                                        {
                                                            "option2": str(sh.cell_value(i, 14)).strip(),
                                                            "score": sh.cell_value(i, 15),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + child).first().id for
                                                                child in
                                                                str(sh.cell_value(i, 16)).strip().split(',') if
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        subfuncins.id) + child) is not None] if ',' in str(
                                                                sh.cell_value(i,
                                                                              16)).strip()
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + str(
                                                                    sh.cell_value(i, 16)).strip()) is None else
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    subfuncins.id) + str(
                                                                    sh.cell_value(i, 16)).strip()).first().id
                                                            if sh.cell_value(i, 16) != ''
                                                            else 0
                                                        }
                                                    ]
                                                    maxscore = max(int(sh.cell_value(i, 12)),
                                                                   int(sh.cell_value(i, 15)))
                                                elif str(sh.cell_value(i, 10)).strip() == 'Multi choice':
                                                    k = 1
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): str(
                                                                        sh.cell_value(i, j)).strip(),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child).first().id
                                                                        for
                                                                        child in
                                                                        str(sh.cell_value(i, j + 2)).strip().split(
                                                                            ',')
                                                                        if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child) is
                                                                        not None] if ',' in str(sh.cell_value(
                                                                        i, j + 2)).strip()
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + str(sh.cell_value(i,
                                                                                                               j + 2)).
                                                                                        strip()) is None
                                                                    else Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + str(
                                                                            sh.cell_value(i,
                                                                                          j + 2)).strip()).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            maxscore = maxscore + int(sh.cell_value(i, j + 1))
                                                            k = k + 1
                                                        else:
                                                            break
                                                elif str(sh.cell_value(i, 10)).strip() == 'Single choice':
                                                    k = 1
                                                    scores = []
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): str(
                                                                        sh.cell_value(i, j)).strip(),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child).first().id
                                                                        for
                                                                        child in
                                                                        str(sh.cell_value(i, j + 2)).strip().split(
                                                                            ',')
                                                                        if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                subfuncins.id) + child) is
                                                                        not None] if ',' in str(sh.cell_value(
                                                                        i, j + 2)).strip()
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + str(sh.cell_value(i,
                                                                                                               j + 2)).
                                                                                        strip()) is None
                                                                    else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            subfuncins.id) + str(sh.cell_value(i, j +
                                                                                                               2)).
                                                                                        strip()).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            scores.append(int(sh.cell_value(i, j + 1)))
                                                            k = k + 1
                                                        else:
                                                            break
                                                        maxscore = max(scores)
                                                quesins = Question(str(sh.cell_value(i, 8)).strip(),
                                                                   str(sh.cell_value(i, 10)).strip(), answers,
                                                                   maxscore,
                                                                   subfuncins.id,
                                                                   findfuncdata.id, findareadata.id,
                                                                   projins.id,
                                                                   combination, sh.cell_value(i, 8),
                                                                   session['empid'])
                                                db.session.add(quesins)
                                                db.session.commit()
                                                for a in answers:
                                                    if a['childquestionid'] != 0:
                                                        if isinstance(a['childquestionid'], list):
                                                            for c in a['childquestionid']:
                                                                data = Question.query.filter_by(id=c)
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d
                                                                          in data]
                                                                quesdatabefore = result[0]
                                                                result.clear()
                                                                if data.first() is not None:
                                                                    data.first().isdependentquestion = 1
                                                                    data.first().modifiedby = session['empid']
                                                                    data.first().islocked = 0
                                                                    db.session.add(data.first())
                                                                    db.session.commit()
                                                                    data = Question.query.filter_by(id=c)
                                                                    result = [{col: getattr(d, col) for col in colsquestion}
                                                                              for
                                                                              d in data]
                                                                    quesdataafter = result[0]
                                                                    result.clear()
                                                                    # region call audit trail method
                                                                    auditins = Audittrail("QUESTION", "UPDATE",
                                                                                          str(quesdatabefore),
                                                                                          str(quesdataafter),
                                                                                          session['empid'])
                                                                    db.session.add(auditins)
                                                                    db.session.commit()
                                                                    # end region
                                                        else:
                                                            data = Question.query.filter_by(id=a['childquestionid'])
                                                            result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                      in data]
                                                            quesdatabefore = result[0]
                                                            result.clear()
                                                            if data.first() is not None:
                                                                data.first().isdependentquestion = 1
                                                                data.first().modifiedby = session['empid']
                                                                data.first().islocked = 0
                                                                db.session.add(data.first())
                                                                db.session.commit()
                                                                data = Question.query.filter_by(id=a['childquestionid'])
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d in data]
                                                                quesdataafter = result[0]
                                                                result.clear()
                                                                # region call audit trail method
                                                                auditins = Audittrail("QUESTION", "UPDATE",
                                                                                      str(quesdatabefore),
                                                                                      str(quesdataafter),
                                                                                      session['empid'])
                                                                db.session.add(auditins)
                                                                db.session.commit()
                                                                # end region
                                                data = Question.query.filter_by(id=quesins.id)
                                                results = [{col: getattr(d, col) for col in colsquestion} for d in
                                                           data]
                                                # region call audit trail method
                                                auditins = Audittrail("QUESTION", "ADD", None, str(results[0]),
                                                                      session['empid'])
                                                db.session.add(auditins)
                                                db.session.commit()
                                                # end region
                                            else:
                                                pass
                                        else:
                                            # add questions in sub func which already exists
                                            findsubfuncdata = Subfunctionality.query.filter(Subfunctionality.name ==
                                                                                            sh.cell_value(i, 5),
                                                                                            Subfunctionality.func_id
                                                                                            == findfuncdata.id). \
                                                one_or_none()
                                            combination = str(projins.id) + str(findareadata.id) + str(
                                                findfuncdata.id) + str(findsubfuncdata.id) + str(
                                                sh.cell_value(i, 8))
                                            existing_question = Question.query.filter(
                                                Question.combination == combination).one_or_none()
                                            if existing_question is None:
                                                maxscore = 0
                                                answers = []
                                                if sh.cell_value(i, 10) == 'Yes / No':
                                                    answers = [
                                                        {
                                                            "option1": sh.cell_value(i, 11),
                                                            "score": sh.cell_value(i, 12),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + child).first().id for
                                                                child in
                                                                sh.cell_value(i, 13).split(',') if
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        findsubfuncdata.id) +
                                                                                child) is not None] if ',' in sh.cell_value(
                                                                i, 13)
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + sh.cell_value(i, 13)) is None else
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + sh.cell_value(i, 13)).first().id
                                                            if sh.cell_value(i, 13) != ''
                                                            else 0
                                                        },
                                                        {
                                                            "option2": sh.cell_value(i, 14),
                                                            "score": sh.cell_value(i, 15),
                                                            "childquestionid": [
                                                                Question.query.filter_by(combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + child).first().id for
                                                                child in
                                                                sh.cell_value(i, 16).split(',') if
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        findsubfuncdata.id) +
                                                                                child) is not None] if ',' in sh.cell_value(
                                                                i, 16)
                                                            else 0 if Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + sh.cell_value(i, 16)) is None else
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + str(
                                                                    findsubfuncdata.id) + sh.cell_value(i, 16)).first().id
                                                            if sh.cell_value(i, 16) != ''
                                                            else 0
                                                        }
                                                    ]
                                                    maxscore = max(int(sh.cell_value(i, 12)),
                                                                   int(sh.cell_value(i, 15)))
                                                elif sh.cell_value(i, 10) == 'Multi choice':
                                                    k = 1
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): sh.cell_value(i, j),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child).first().id
                                                                        for
                                                                        child in
                                                                        sh.cell_value(i, j + 2).split(',') if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child) is
                                                                        not None] if ',' in sh.cell_value(
                                                                        i, j + 2)
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) +
                                                                                    sh.cell_value(i, j + 2)) is None else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) +
                                                                                    sh.cell_value(i, j + 2)).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            maxscore = maxscore + int(sh.cell_value(i, j + 1))
                                                            k = k + 1
                                                        else:
                                                            break
                                                elif sh.cell_value(i, 10) == 'Single choice':
                                                    k = 1
                                                    scores = []
                                                    for j in range(11, sh.ncols, 3):
                                                        if sh.cell_value(i, j) != '':
                                                            answers.append(
                                                                {
                                                                    "option{0}".format(k): sh.cell_value(i, j),
                                                                    "score": sh.cell_value(i, j + 1),
                                                                    "childquestionid": [
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child).first().id
                                                                        for
                                                                        child in
                                                                        sh.cell_value(i, j + 2).split(',') if
                                                                        Question.query.filter_by(
                                                                            combination=str(projins.id) + str(
                                                                                findareadata.id) + str(
                                                                                findfuncdata.id) + str(
                                                                                findsubfuncdata.id) + child) is
                                                                        not None] if ',' in sh.cell_value(
                                                                        i, j + 2)
                                                                    else 0 if Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) +
                                                                                    sh.cell_value(i, j + 2)) is None else
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + str(
                                                                            findsubfuncdata.id) +
                                                                                    sh.cell_value(i, j + 2)).first().id
                                                                    if sh.cell_value(i, j + 2) != ''
                                                                    else 0
                                                                })
                                                            scores.append(int(sh.cell_value(i, j + 1)))
                                                            k = k + 1
                                                        else:
                                                            break
                                                        maxscore = max(scores)
                                                quesins = Question(sh.cell_value(i, 8), sh.cell_value(i, 10),
                                                                   answers,
                                                                   maxscore,
                                                                   findsubfuncdata.id,
                                                                   findfuncdata.id, findareadata.id,
                                                                   projins.id,
                                                                   combination, sh.cell_value(i, 9),
                                                                   session['empid'])
                                                db.session.add(quesins)
                                                db.session.commit()
                                                for a in answers:
                                                    if a['childquestionid'] != 0:
                                                        if isinstance(a['childquestionid'], list):
                                                            for c in a['childquestionid']:
                                                                data = Question.query.filter_by(id=c)
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d
                                                                          in data]
                                                                quesdatabefore = result[0]
                                                                result.clear()
                                                                if data.first() is not None:
                                                                    data.first().isdependentquestion = 1
                                                                    data.first().modifiedby = session['empid']
                                                                    data.first().islocked = 0
                                                                    db.session.add(data.first())
                                                                    db.session.commit()
                                                                    data = Question.query.filter_by(id=c)
                                                                    result = [{col: getattr(d, col) for col in colsquestion}
                                                                              for
                                                                              d in data]
                                                                    quesdataafter = result[0]
                                                                    result.clear()
                                                                    # region call audit trail method
                                                                    auditins = Audittrail("QUESTION", "UPDATE",
                                                                                          str(quesdatabefore),
                                                                                          str(quesdataafter),
                                                                                          session['empid'])
                                                                    db.session.add(auditins)
                                                                    db.session.commit()
                                                                    # end region
                                                        else:
                                                            data = Question.query.filter_by(id=a['childquestionid'])
                                                            result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                      in data]
                                                            quesdatabefore = result[0]
                                                            result.clear()
                                                            if data.first() is not None:
                                                                data.first().isdependentquestion = 1
                                                                data.first().modifiedby = session['empid']
                                                                data.first().islocked = 0
                                                                db.session.add(data.first())
                                                                db.session.commit()
                                                                data = Question.query.filter_by(id=a['childquestionid'])
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d in data]
                                                                quesdataafter = result[0]
                                                                result.clear()
                                                                # region call audit trail method
                                                                auditins = Audittrail("QUESTION", "UPDATE",
                                                                                      str(quesdatabefore),
                                                                                      str(quesdataafter),
                                                                                      session['empid'])
                                                                db.session.add(auditins)
                                                                db.session.commit()
                                                                # end region
                                                data = Question.query.filter_by(id=quesins.id)
                                                results = [{col: getattr(d, col) for col in colsquestion} for d in
                                                           data]
                                                # region call audit trail method
                                                auditins = Audittrail("QUESTION", "ADD", None, str(results[0]),
                                                                      session['empid'])
                                                db.session.add(auditins)
                                                db.session.commit()
                                                # end region
                                            else:
                                                pass
                                    else:
                                        # add questions in func when subfunc does not exists for this func
                                        findfuncdata = Functionality.query.filter_by(
                                            name=str(sh.cell_value(i, 2)).strip(),
                                            area_id=findareadata.id).first()
                                        combination = str(projins.id) + str(findareadata.id) + str(
                                            findfuncdata.id) + str(sh.cell_value(i, 8)).strip()
                                        existing_question = Question.query.filter(
                                            Question.combination == combination).one_or_none()
                                        if existing_question is None:
                                            maxscore = 0
                                            answers = []
                                            if str(sh.cell_value(i, 10)).strip() == 'Yes / No':
                                                answers = [
                                                    {
                                                        "option1": str(sh.cell_value(i, 11)).strip(),
                                                        "score": sh.cell_value(i, 12),
                                                        "childquestionid": [
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + child).first().id for
                                                            child in
                                                            str(sh.cell_value(i, 13)).strip().split(',') if
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + child) is not None] if ',' in str(
                                                            sh.cell_value(i,
                                                                          13)).strip()
                                                        else 0 if Question.query.filter_by(
                                                            combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                sh.cell_value(i, 13)).strip()) is None else
                                                        Question.query.filter_by(
                                                            combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                sh.cell_value(i, 13)).strip()).first().id
                                                        if sh.cell_value(i, 13) != ''
                                                        else 0
                                                    },
                                                    {
                                                        "option2": str(sh.cell_value(i, 14)).strip(),
                                                        "score": sh.cell_value(i, 15),
                                                        "childquestionid": [
                                                            Question.query.filter_by(combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + child).first().id for
                                                            child in
                                                            str(sh.cell_value(i, 16)).strip().split(',') if
                                                            Question.query.filter_by(
                                                                combination=str(projins.id) + str(
                                                                    findareadata.id) + str(
                                                                    findfuncdata.id) + child) is not None] if ',' in str(
                                                            sh.cell_value(i,
                                                                          16)).strip()
                                                        else 0 if Question.query.filter_by(
                                                            combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                sh.cell_value(i, 16)).strip()) is None else
                                                        Question.query.filter_by(
                                                            combination=str(projins.id) + str(
                                                                findareadata.id) + str(
                                                                findfuncdata.id) + str(
                                                                sh.cell_value(i, 16)).strip()).first().id
                                                        if sh.cell_value(i, 16) != ''
                                                        else 0
                                                    }
                                                ]
                                                maxscore = max(int(sh.cell_value(i, 12)), int(sh.cell_value(i, 15)))
                                            elif str(sh.cell_value(i, 10)).strip() == 'Multi choice':
                                                k = 1
                                                for j in range(11, sh.ncols, 3):
                                                    if sh.cell_value(i, j) != '':
                                                        answers.append(
                                                            {
                                                                "option{0}".format(k): str(
                                                                    sh.cell_value(i, j)).strip(),
                                                                "score": sh.cell_value(i, j + 1),
                                                                "childquestionid": [
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child).first().id
                                                                    for
                                                                    child in
                                                                    str(sh.cell_value(i, j + 2)).strip().split(',')
                                                                    if
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child) is
                                                                    not None] if ',' in str(sh.cell_value(i,
                                                                                                          j +
                                                                                                          2)).strip()
                                                                else 0 if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) +
                                                                                str(sh.cell_value(i,
                                                                                                  j + 2)).strip()) is None
                                                                else Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) + str(
                                                                        sh.cell_value(i, j + 2)).strip()).first().id
                                                                if sh.cell_value(i, j + 2) != ''
                                                                else 0
                                                            })
                                                        maxscore = maxscore + int(sh.cell_value(i, j + 1))
                                                        k = k + 1
                                                    else:
                                                        break
                                            elif str(sh.cell_value(i, 10)).strip() == 'Single choice':
                                                k = 1
                                                scores = []
                                                for j in range(11, sh.ncols, 3):
                                                    if sh.cell_value(i, j) != '':
                                                        answers.append(
                                                            {
                                                                "option{0}".format(k): str(
                                                                    sh.cell_value(i, j)).strip(),
                                                                "score": sh.cell_value(i, j + 1),
                                                                "childquestionid": [
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child).first().id
                                                                    for
                                                                    child in
                                                                    str(sh.cell_value(i, j + 2)).strip().split(',')
                                                                    if
                                                                    Question.query.filter_by(
                                                                        combination=str(projins.id) + str(
                                                                            findareadata.id) + str(
                                                                            findfuncdata.id) + child) is
                                                                    not None] if ',' in str(sh.cell_value(i,
                                                                                                          j +
                                                                                                          2)).strip()
                                                                else 0 if Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) +
                                                                                str(sh.cell_value(i,
                                                                                                  j + 2)).strip()) is None
                                                                else
                                                                Question.query.filter_by(
                                                                    combination=str(projins.id) + str(
                                                                        findareadata.id) + str(
                                                                        findfuncdata.id) +
                                                                                str(sh.cell_value(i, j + 2)).
                                                                                    strip()).first().id
                                                                if sh.cell_value(i, j + 2) != ''
                                                                else 0
                                                            })
                                                        scores.append(int(sh.cell_value(i, j + 1)))
                                                        k = k + 1
                                                    else:
                                                        break
                                                    maxscore = max(scores)
                                            quesins = Question(str(sh.cell_value(i, 8)).strip(),
                                                               str(sh.cell_value(i, 10)).strip(), answers,
                                                               maxscore,
                                                               None,
                                                               findfuncdata.id, findareadata.id, projins.id,
                                                               combination, sh.cell_value(i, 9), session['empid'])
                                            db.session.add(quesins)
                                            db.session.commit()
                                            for a in answers:
                                                if a['childquestionid'] != 0:
                                                    if isinstance(a['childquestionid'], list):
                                                        for c in a['childquestionid']:
                                                            data = Question.query.filter_by(id=c)
                                                            result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                      in data]
                                                            quesdatabefore = result[0]
                                                            result.clear()
                                                            if data.first() is not None:
                                                                data.first().isdependentquestion = 1
                                                                data.first().modifiedby = session['empid']
                                                                data.first().islocked = 0
                                                                db.session.add(data.first())
                                                                db.session.commit()
                                                                data = Question.query.filter_by(id=c)
                                                                result = [{col: getattr(d, col) for col in colsquestion} for
                                                                          d in data]
                                                                quesdataafter = result[0]
                                                                result.clear()
                                                                # region call audit trail method
                                                                auditins = Audittrail("QUESTION", "UPDATE",
                                                                                      str(quesdatabefore),
                                                                                      str(quesdataafter),
                                                                                      session['empid'])
                                                                db.session.add(auditins)
                                                                db.session.commit()
                                                                # end region
                                                    else:
                                                        data = Question.query.filter_by(id=a['childquestionid'])
                                                        result = [{col: getattr(d, col) for col in colsquestion} for d
                                                                  in data]
                                                        quesdatabefore = result[0]
                                                        result.clear()
                                                        if data.first() is not None:
                                                            data.first().isdependentquestion = 1
                                                            data.first().modifiedby = session['empid']
                                                            data.first().islocked = 0
                                                            db.session.add(data.first())
                                                            db.session.commit()
                                                            data = Question.query.filter_by(id=a['childquestionid'])
                                                            result = [{col: getattr(d, col) for col in colsquestion} for
                                                                      d in data]
                                                            quesdataafter = result[0]
                                                            result.clear()
                                                            # region call audit trail method
                                                            auditins = Audittrail("QUESTION", "UPDATE",
                                                                                  str(quesdatabefore),
                                                                                  str(quesdataafter),
                                                                                  session['empid'])
                                                            db.session.add(auditins)
                                                            db.session.commit()
                                                            # end region
                                            data = Question.query.filter_by(id=quesins.id)
                                            results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                            # region call audit trail method
                                            auditins = Audittrail("QUESTION", "ADD", None, str(results[0]),
                                                                  session['empid'])
                                            db.session.add(auditins)
                                            db.session.commit()
                                            # end region
                                        else:
                                            pass
                                return make_response(jsonify({"message": f"Project {projname}"
                                                                         f" has been successfully added with"
                                                                         f" the questions in the "
                                                                         f"uploaded file",
                                                              "data": newaddedproject})), 201
                            else:
                                return make_response(jsonify({"message": f"Project {projname} has been successfully added.",
                                                              "data": newaddedproject})), 201
                        else:
                            data_comp = Companydetails.query.filter_by(id=comp_id).first()
                            return make_response(jsonify({"message": f"Project {projname} already exists for company "
                                                                     f"{data_comp.companyname}."})), 400
                    else:
                        return make_response(jsonify({"message": "Quota for no. of projects as per previous licensing "
                                                                 "is full. Please contact DevOps Enabler "
                                                                 "support team to renew further !!"})), 400
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@project.route('/api/updelproject/', methods=['POST', 'PUT', 'DELETE'])
def updelproject():
    """
        ---
        post:
          description: Fetch a project.
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
              - updatedeleteproject
        put:
          description: Update a project.
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
              - updatedeleteproject
        delete:
          description: Delete a project.
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
              - updatedeleteproject
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
                projid = res['projectid']
                data = Project.query.filter_by(id=projid)
                for d in data:
                    json_data = mergedict({'id': d.id},
                                          {'name': d.name},
                                          {'description': d.description},
                                          {'levels': d.levels},
                                          {'companyid': d.companyid},
                                          {'achievedlevel': d.achievedlevel},
                                          {'needforreview': d.needforreview},
                                          {'assessmentcompletion': str(d.assessmentcompletion)},
                                          {'achievedpercentage': str(d.achievedpercentage)},
                                          {'creationdatetime': d.creationdatetime},
                                          {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                          {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                          {'updationdatetime': d.updationdatetime},
                                          {'createdby': d.createdby},
                                          {'modifiedby': d.modifiedby})
                    results.append(json_data)
                projdatabefore = results[0]
                results.clear()
                if data.first() is None:
                    return make_response(jsonify({"message": "Incorrect ID"})), 404
                else:
                    if request.method == 'POST':
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'levels': d.levels},
                                                  {'companyid': d.companyid},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'needforreview': d.needforreview},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime})
                            results.append(json_data)
                        return make_response(jsonify({"data": results[0]})), 200
                    elif request.method == 'PUT':
                        projdesc = res['ProjectDescription']
                        levels = res['Levels']
                        if 'NeedForReview' in res:
                            nfr = res['NeedForReview']
                        else:
                            nfr = 1
                        data.first().description = projdesc
                        data.first().levels = levels
                        data.first().needforreview = nfr
                        data.first().modifiedby = session['empid']
                        db.session.add(data.first())
                        db.session.commit()
                        data = Project.query.filter_by(id=projid)
                        for d in data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'levels': d.levels},
                                                  {'companyid': d.companyid},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'needforreview': d.needforreview},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        projdataafter = results[0]
                        # region call audit trail method
                        auditins = Audittrail("PROJECT", "UPDATE", str(projdatabefore), str(projdataafter),
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region
                        return make_response(jsonify({"message": f"Project {data.first().name} "
                                                                 f"successfully updated."})), 200
                    elif request.method == 'DELETE':

                        projectmanager = Projectassignmenttomanager.query.filter_by(project_id=projid)
                        if projectmanager.first() is not None:
                            empid = projectmanager.first().emp_id
                            userdata = Companyuserdetails.query.filter_by(empid=empid).first()
                            empname = userdata.empname
                            companyid = userdata.companyid
                            mailto = userdata.empemail
                            project_details = Project.query.filter_by(id=projid)
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
                                event_name="DELETEPROJECTTOMANAGER").first()
                            mail_subject = notification_data.mail_subject
                            mail_body = str(notification_data.mail_body).format(empname=empname,
                                                                                projectname=project_details.first().name)
                            mailout = trigger_mail(mailfrom, mailto, host, pwd, mail_subject, empname, mail_body)
                            print("======", mailout)
                            # end region

                        db.session.delete(data.first())
                        db.session.commit()
                        # region call audit trail method
                        auditins = Audittrail("PROJECT", "DELETE", str(projdatabefore), None,
                                              session['empid'])
                        db.session.add(auditins)
                        db.session.commit()
                        # end region

                        data_area = Area.query.filter_by(projectid=projid)
                        if data_area is not None:
                            for a in data_area:
                                json_data = mergedict({'id': a.id},
                                                      {'name': a.name},
                                                      {'description': a.description},
                                                      {'projectid': a.projectid},
                                                      {'assessmentcompletion': str(a.assessmentcompletion)},
                                                      {'achievedpercentage': str(a.achievedpercentage)},
                                                      {'achievedlevel': a.achievedlevel},
                                                      {'creationdatetime': a.creationdatetime},
                                                      {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                      {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                      {'updationdatetime': a.updationdatetime},
                                                      {'createdby': a.createdby},
                                                      {'modifiedby': a.modifiedby})
                                results.append(json_data)
                                db.session.delete(a)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("AREA", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        data_func = Functionality.query.filter_by(proj_id=projid)
                        if data_func is not None:
                            for f in data_func:
                                json_data = mergedict({'id': f.id},
                                                      {'name': f.name},
                                                      {'description': f.description},
                                                      {'retake_assessment_days': f.retake_assessment_days},
                                                      {'area_id': f.area_id},
                                                      {'proj_id': f.proj_id},
                                                      {'assessmentcompletion': str(f.assessmentcompletion)},
                                                      {'achievedpercentage': str(f.achievedpercentage)},
                                                      {'achievedlevel': f.achievedlevel},
                                                      {'creationdatetime': f.creationdatetime},
                                                      {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                      {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                      {'updationdatetime': f.updationdatetime},
                                                      {'createdby': f.createdby},
                                                      {'modifiedby': f.modifiedby})
                                results.append(json_data)
                                db.session.delete(f)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("FUNCTIONALITY", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        data_subfunc = Subfunctionality.query.filter_by(proj_id=projid)
                        if data_subfunc is not None:
                            for s in data_subfunc:
                                data = Subfunctionality.query.filter_by(id=s.id)
                                results = [{col: getattr(d, col) for col in cols_subfunc} for d in data]
                                db.session.delete(s)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("SUB-FUNCTIONALITY", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        data_question = Question.query.filter_by(proj_id=projid)
                        if data_question is not None:
                            for q in data_question:
                                data = Question.query.filter_by(id=q.id)
                                results = [{col: getattr(d, col) for col in colsquestion} for d in data]
                                db.session.delete(q)
                                db.session.commit()
                                # region call audit trail method
                                auditins = Audittrail("QUESTION", "DELETE", str(results[0]), None,
                                                      session['empid'])
                                db.session.add(auditins)
                                db.session.commit()
                                # end region
                                results.clear()
                        return make_response(jsonify({"message": f"Project with ID {projid} "
                                                                 f"successfully deleted."})), 204
            else:
                return make_response(jsonify({"message": resp})), 401
        else:
            return make_response(jsonify({"message": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
