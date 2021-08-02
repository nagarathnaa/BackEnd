from flask import Blueprint, session, request, jsonify, make_response
import requests
from DOEAssessmentApp import db
from DOEAssessmentApp.DOE_models.assessment_model import Assessment
from DOEAssessmentApp.DOE_models.project_model import Project
from DOEAssessmentApp.DOE_models.area_model import Area
from DOEAssessmentApp.DOE_models.functionality_model import Functionality
from DOEAssessmentApp.DOE_models.sub_functionality_model import Subfunctionality
from DOEAssessmentApp.DOE_models.trn_team_member_assessment_model import QuestionsAnswered
from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from DOEAssessmentApp.DOE_models.audittrail_model import Audittrail

reports = Blueprint('reports', __name__)


def mergedict(*args):
    output = {}
    for arg in args:
        output.update(arg)
    return output


@reports.route('/api/achievedpercentagebyprojects', methods=['POST'])
def achievedpercentagebyprojects():
    """
        ---
        post:
          description: Achieved percentage by projects.
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
              - getachievedpercentagebyproject
    """
    try:
        results = []
        assessmentcompletionforproj = 0
        achievedpercentageforproj = 0
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
                    data = Project.query.filter_by(id=projid)
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'levels': d.levels},
                                              {'companyid': d.companyid},
                                              {'assessmentcompletion': str(d.assessmentcompletion)},
                                              {'achievedpercentage': str(d.achievedpercentage)},
                                              {'achievedlevel': d.achievedlevel},
                                              {'needforreview': d.needforreview},
                                              {'creationdatetime': d.creationdatetime},
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    projectdatabefore = results[0]
                    results.clear()
                    area_data = Area.query.filter(Area.projectid == projid)
                    areacount = Area.query.filter_by(projectid=projid).count()
                    if areacount > 0:
                        for adata in area_data:
                            my_headers = {'Authorization': 'Bearer {0}'.format(auth_token),
                                          'Content-type': 'application/json'}
                            response = requests.post('http://0.0.0.0:5000/api/achievedpercentagebyarea',
                                                     json={'area_id': adata.id,
                                                           'projectid': projid}, headers=my_headers)
                            scode = response.status_code
                            print(scode, flush=True)
                            print(response.json(), flush=True)
                            if scode == 200:
                                assessmentcompletionforproj = assessmentcompletionforproj + int(
                                    float(response.json()['assessmentcompletion']))
                                achievedpercentageforproj = achievedpercentageforproj + int(
                                    float(response.json()['achievedpercentage']))
                        assessmentcompletion = assessmentcompletionforproj / areacount
                        achievedpercentage = achievedpercentageforproj / areacount
                        try:
                            project_data = Project.query.filter_by(id=projid)
                            prevassessmentcompletion = project_data.first().assessmentcompletion
                            if prevassessmentcompletion != assessmentcompletion:
                                project_data.first().prevassessmentcompletion = prevassessmentcompletion
                            project_data.first().assessmentcompletion = assessmentcompletion
                            prevachievedpercentage = project_data.first().achievedpercentage
                            if prevachievedpercentage != achievedpercentage:
                                project_data.first().prevachievedpercentage = prevachievedpercentage
                            project_data.first().achievedpercentage = achievedpercentage
                            leveldata = Project.query.filter(Project.id == projid)
                            if leveldata.first() is not None:
                                for level in leveldata.first().levels:
                                    if (achievedpercentage >= level['RangeFrom']) and (
                                            achievedpercentage <= level['RangeTo']):
                                        achievedlevel = level['LevelName']
                                        break
                            else:
                                achievedlevel = ''
                            project_data.first().achievedlevel = achievedlevel
                            project_data.first().modifiedby = None
                            db.session.add(project_data.first())
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        proj_data = Project.query.filter_by(id=projid)
                        for d in proj_data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'levels': d.levels},
                                                  {'companyid': d.companyid},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'needforreview': d.needforreview},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        projectdataafter = results[0]
                        # region call audit trail method
                        try:
                            auditins = Audittrail("PROJECT", "UPDATE", str(projectdatabefore), str(projectdataafter),
                                                  None)
                            db.session.add(auditins)
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        # end region
                        d = Project.query.filter_by(id=projid).first()
                        return make_response(jsonify({"assessmentcompletion": str(d.assessmentcompletion),
                                                      "achievedpercentage": str(d.achievedpercentage),
                                                      "achievedlevel": d.achievedlevel,
                                                      "prevassessmentcompletion": str(d.prevassessmentcompletion),
                                                      "prevachievedpercentage": str(
                                                          d.prevachievedpercentage)})), 200
                    else:
                        return make_response(jsonify({"msg": "No Area data found!!"})), 404
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@reports.route('/api/achievedpercentagebyarea', methods=['POST'])
def achievedpercentagebyarea():
    """
        ---
        post:
          description: Achieved percentage by areas.
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
              - getachievedpercentagebyarea
    """
    try:
        results = []
        assessmentcompletionforarea = 0
        achievedpercentageforarea = 0
        achievedlevel = ''
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "POST":
                    res = request.get_json(force=True)
                    projid = res['projectid']
                    area_id = res['area_id']
                    data = Area.query.filter_by(id=area_id)
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'projectid': d.projectid},
                                              {'assessmentcompletion': str(d.assessmentcompletion)},
                                              {'achievedpercentage': str(d.achievedpercentage)},
                                              {'achievedlevel': d.achievedlevel},
                                              {'creationdatetime': d.creationdatetime},
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    areadatabefore = results[0]
                    results.clear()
                    functionality_data = Functionality.query.filter(Functionality.proj_id == projid,
                                                                    Functionality.area_id == area_id)
                    funccount = Functionality.query.filter_by(proj_id=projid,
                                                              area_id=area_id).count()
                    if funccount > 0:
                        for fdata in functionality_data:
                            my_headers = {'Authorization': 'Bearer {0}'.format(auth_token),
                                          'Content-type': 'application/json'}
                            response = requests.post('http://0.0.0.0:5000/api/achievedpercentagebyfunctionality',
                                                     json={'functionality_id': fdata.id,
                                                           'area_id': area_id,
                                                           'projectid': projid}, headers=my_headers)
                            scode = response.status_code
                            print(scode, flush=True)
                            print(response.json(), flush=True)
                            if scode == 200:
                                assessmentcompletionforarea = assessmentcompletionforarea + int(
                                    float(response.json()['assessmentcompletion']))
                                achievedpercentageforarea = achievedpercentageforarea + int(
                                    float(response.json()['achievedpercentage']))
                        assessmentcompletion = assessmentcompletionforarea / funccount
                        achievedpercentage = achievedpercentageforarea / funccount
                        try:
                            area_data = Area.query.filter_by(id=area_id)
                            prevassessmentcompletion = area_data.first().assessmentcompletion
                            if prevassessmentcompletion != assessmentcompletion:
                                area_data.first().prevassessmentcompletion = prevassessmentcompletion
                            area_data.first().assessmentcompletion = assessmentcompletion
                            prevachievedpercentage = area_data.first().achievedpercentage
                            if prevachievedpercentage != achievedpercentage:
                                area_data.first().prevachievedpercentage = prevachievedpercentage
                            area_data.first().achievedpercentage = achievedpercentage
                            leveldata = Project.query.filter(Project.id == projid)
                            if leveldata.first() is not None:
                                for level in leveldata.first().levels:
                                    if (achievedpercentage >= level['RangeFrom']) and (
                                            achievedpercentage <= level['RangeTo']):
                                        achievedlevel = level['LevelName']
                                        break
                            else:
                                achievedlevel = ''
                            area_data.first().achievedlevel = achievedlevel
                            area_data.first().modifiedby = None
                            db.session.add(area_data.first())
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        adata = Area.query.filter_by(id=area_id)
                        for d in adata:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'projectid': d.projectid},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        areadataafter = results[0]
                        # region call audit trail method
                        try:
                            auditins = Audittrail("AREA", "UPDATE", str(areadatabefore), str(areadataafter),
                                                  None)
                            db.session.add(auditins)
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        # end region
                        d = Area.query.filter_by(id=area_id).first()
                        return make_response(jsonify({"assessmentcompletion": str(d.assessmentcompletion),
                                                      "achievedpercentage": str(d.achievedpercentage),
                                                      "achievedlevel": d.achievedlevel,
                                                      "prevassessmentcompletion": str(d.prevassessmentcompletion),
                                                      "prevachievedpercentage": str(
                                                          d.prevachievedpercentage)})), 200
                    else:
                        return make_response(jsonify({"msg": "No Functionality data found!!"})), 404
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@reports.route('/api/achievedpercentagebyfunctionality', methods=['POST'])
def achievedpercentagebyfunctionality():
    """
        ---
        post:
          description: Achieved percentage by functionality.
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
              - getachievedpercentagebyfunctionality
    """
    try:
        results = []
        recommendation = None
        assessmentcompletionforfunc = 0
        achievedpercentageforfunc = 0
        countofnaques = 0
        countofquestionanswered = 0
        scoreachievedforthefunc = 0
        countofquestions = 0
        maxscoreforthefunc = 0
        achievedlevel = ''
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "POST":
                    res = request.get_json(force=True)
                    projid = res['projectid']
                    area_id = res['area_id']
                    functionality_id = res['functionality_id']
                    data = Functionality.query.filter_by(id=functionality_id)
                    for d in data:
                        json_data = mergedict({'id': d.id},
                                              {'name': d.name},
                                              {'description': d.description},
                                              {'priority': d.priority},
                                              {'recommendation': d.recommendation},
                                              {'retake_assessment_days': d.retake_assessment_days},
                                              {'area_id': d.area_id},
                                              {'proj_id': d.proj_id},
                                              {'assessmentcompletion': str(d.assessmentcompletion)},
                                              {'achievedpercentage': str(d.achievedpercentage)},
                                              {'achievedlevel': d.achievedlevel},
                                              {'creationdatetime': d.creationdatetime},
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    functionalitydatabefore = results[0]
                    results.clear()
                    # region 'when assessment not assigned to sub-functionality and directly to functionality
                    assessment_data = Assessment.query.filter_by(projectid=projid,
                                                                 area_id=area_id,
                                                                 functionality_id=functionality_id,
                                                                 subfunctionality_id=None,
                                                                 assessmentstatus="COMPLETED",
                                                                 employeeassignedstatus=1,
                                                                 active=1)
                    if assessment_data.count() > 0:
                        for data in assessment_data:
                            countofquestions = countofquestions + data.countoftotalquestions
                            cofquesanswdperassessment = QuestionsAnswered.query.filter_by(assignmentid=data.id,
                                                                                          active=1,
                                                                                          applicability=1).count()
                            cofnaquesperassessment = QuestionsAnswered.query.filter_by(assignmentid=data.id,
                                                                                       active=1,
                                                                                       applicability=0).count()
                            countofnaques = countofnaques + cofnaquesperassessment
                            countofquestionanswered = countofquestionanswered + cofquesanswdperassessment
                            scoreachievedforthefunc = scoreachievedforthefunc + data.totalscoreachieved
                            maxscoreforthefunc = maxscoreforthefunc + data.totalmaxscore
                        if countofnaques != 0:
                            countofquestions = countofquestions - countofnaques
                        if countofquestions != 0:
                            assessmentcompletion = ((countofquestionanswered / assessment_data.
                                                     count()) / countofquestions) * 100
                            achievedpercentage = (scoreachievedforthefunc / maxscoreforthefunc) * 100
                        else:
                            assessmentcompletion = 0
                            achievedpercentage = 0
                        try:
                            functionality_data = Functionality.query.filter_by(id=functionality_id)
                            leveldata = Project.query.filter(Project.id == functionality_data.first().proj_id)
                            if leveldata.first() is not None:
                                for level in leveldata.first().levels:
                                    if (achievedpercentage >= level['RangeFrom']) and (
                                            achievedpercentage <= level['RangeTo']):
                                        achievedlevel = level['LevelName']
                                        break
                            else:
                                achievedlevel = ''
                            prevassessmentcompletion = functionality_data.first().assessmentcompletion
                            if prevassessmentcompletion != assessmentcompletion:
                                functionality_data.first().prevassessmentcompletion = prevassessmentcompletion
                            functionality_data.first().assessmentcompletion = assessmentcompletion
                            prevachievedpercentage = functionality_data.first().achievedpercentage
                            if prevachievedpercentage != achievedpercentage:
                                functionality_data.first().prevachievedpercentage = prevachievedpercentage
                            functionality_data.first().achievedpercentage = achievedpercentage
                            if functionality_data.first().priority == 1:
                                if (achievedpercentage >= 81) and (achievedpercentage <= 100):
                                    recommendation = "Good !"
                                else:
                                    recommendation = "Needs improvement ! Maturity should be more than 80%. Follow" \
                                                     " the general recommendations to improve !!"
                            elif functionality_data.first().priority == 2:
                                if (achievedpercentage >= 61) and (achievedpercentage <= 80):
                                    recommendation = "Good ! Follow" \
                                                     " the general recommendations to improve further !!"
                                if achievedpercentage >= 81:
                                    recommendation = "Excellent !"
                                else:
                                    recommendation = "Needs improvement ! Maturity should be more than 60%. Follow" \
                                                     " the general recommendations to improve !!"
                            elif functionality_data.first().priority == 3:
                                if (achievedpercentage >= 41) and (achievedpercentage <= 60):
                                    recommendation = "Good ! Follow" \
                                                     " the general recommendations to improve further !!"
                                if achievedpercentage >= 61:
                                    recommendation = "Excellent !"
                                else:
                                    recommendation = "Needs improvement ! Maturity should be more than 40%. Follow" \
                                                     " the general recommendations to improve !!"
                            elif functionality_data.first().priority == 4:
                                if (achievedpercentage >= 21) and (achievedpercentage <= 40):
                                    recommendation = "Good ! Follow" \
                                                     " the general recommendations to improve further !!"
                                if achievedpercentage >= 41:
                                    recommendation = "Excellent !"
                                else:
                                    recommendation = "Needs improvement ! Maturity should be more than 20%. Follow" \
                                                     " the general recommendations to improve !!"
                            elif functionality_data.first().priority == 5:
                                if (achievedpercentage >= 1) and (achievedpercentage <= 20):
                                    recommendation = "Good ! Follow" \
                                                     " the general recommendations to improve further !!"
                                if achievedpercentage >= 21:
                                    recommendation = "Excellent !"
                                else:
                                    recommendation = "Needs improvement ! Maturity should be more than zero. Follow" \
                                                     " the general recommendations to improve !!"
                            functionality_data.first().achievedlevel = achievedlevel
                            functionality_data.first().recommendation = recommendation
                            functionality_data.first().modifiedby = None
                            db.session.add(functionality_data.first())
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        func_data = Functionality.query.filter_by(id=functionality_id)
                        for d in func_data:
                            json_data = mergedict({'id': d.id},
                                                  {'name': d.name},
                                                  {'description': d.description},
                                                  {'priority': d.priority},
                                                  {'recommendation': d.recommendation},
                                                  {'retake_assessment_days': d.retake_assessment_days},
                                                  {'area_id': d.area_id},
                                                  {'proj_id': d.proj_id},
                                                  {'assessmentcompletion': str(d.assessmentcompletion)},
                                                  {'achievedpercentage': str(d.achievedpercentage)},
                                                  {'achievedlevel': d.achievedlevel},
                                                  {'creationdatetime': d.creationdatetime},
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        functionalitydataafter = results[0]
                        # region call audit trail method
                        try:
                            auditins = Audittrail("FUNCTIONALITY", "UPDATE", str(functionalitydatabefore),
                                                  str(functionalitydataafter),
                                                  None)
                            db.session.add(auditins)
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        # end region
                        d = Functionality.query.filter_by(id=functionality_id).first()
                        return make_response(jsonify({"assessmentcompletion": str(d.assessmentcompletion),
                                                      "achievedpercentage": str(d.achievedpercentage),
                                                      "achievedlevel": d.achievedlevel,
                                                      "prevassessmentcompletion": str(d.prevassessmentcompletion),
                                                      "prevachievedpercentage": str(
                                                          d.prevachievedpercentage),
                                                      "recommendation": recommendation})), 200
                    # end region
                    else:
                        subfunctionality_data = Subfunctionality.query.filter(Subfunctionality.proj_id == projid,
                                                                              Subfunctionality.area_id == area_id,
                                                                              Subfunctionality.
                                                                              func_id == functionality_id)
                        subfunccount = Subfunctionality.query.filter_by(proj_id=projid,
                                                                        area_id=area_id,
                                                                        func_id=functionality_id).count()
                        if subfunccount > 0:
                            for sfdata in subfunctionality_data:
                                my_headers = {'Authorization': 'Bearer {0}'.format(auth_token),
                                              'Content-type': 'application/json'}
                                response = requests.post('http://0.0.0.0:5000/api/achievedpercentagebysubfunctionality',
                                                         json={'subfunc_id': sfdata.id,
                                                               'functionality_id': functionality_id,
                                                               'area_id': area_id,
                                                               'projectid': projid}, headers=my_headers)
                                scode = response.status_code
                                print(scode, flush=True)
                                print(response.json(), flush=True)
                                if scode == 200:
                                    assessmentcompletionforfunc = assessmentcompletionforfunc + int(
                                        float(response.json()['assessmentcompletion']))
                                    achievedpercentageforfunc = achievedpercentageforfunc + int(
                                        float(response.json()['achievedpercentage']))
                            assessmentcompletion = (assessmentcompletionforfunc / subfunccount) if \
                                subfunccount > 0 else 0
                            achievedpercentage = (achievedpercentageforfunc / subfunccount) if subfunccount > 0 else 0
                            try:
                                functionality_data = Functionality.query.filter_by(id=functionality_id)
                                leveldata = Project.query.filter(Project.id == functionality_data.first().proj_id)
                                if leveldata.first() is not None:
                                    for level in leveldata.first().levels:
                                        if (achievedpercentage >= level['RangeFrom']) and (
                                                achievedpercentage <= level['RangeTo']):
                                            achievedlevel = level['LevelName']
                                            break
                                else:
                                    achievedlevel = ''
                                prevassessmentcompletion = functionality_data.first().assessmentcompletion
                                if prevassessmentcompletion != assessmentcompletion:
                                    functionality_data.first().prevassessmentcompletion = prevassessmentcompletion
                                functionality_data.first().assessmentcompletion = assessmentcompletion
                                prevachievedpercentage = functionality_data.first().achievedpercentage
                                if prevachievedpercentage != achievedpercentage:
                                    functionality_data.first().prevachievedpercentage = prevachievedpercentage
                                functionality_data.first().achievedpercentage = achievedpercentage
                                if functionality_data.first().priority == 1:
                                    if (achievedpercentage >= 81) and (achievedpercentage <= 100):
                                        recommendation = "Good !"
                                    else:
                                        recommendation = "Needs improvement ! Maturity should be more than 80%. " \
                                                         "Follow the general recommendations to improve !!"
                                elif functionality_data.first().priority == 2:
                                    if (achievedpercentage >= 61) and (achievedpercentage <= 80):
                                        recommendation = "Good ! Follow" \
                                                         " the general recommendations to improve further !!"
                                    if achievedpercentage >= 81:
                                        recommendation = "Excellent !"
                                    else:
                                        recommendation = "Needs improvement ! Maturity should be more than 60%. " \
                                                         "Follow the general recommendations to improve !!"
                                elif functionality_data.first().priority == 3:
                                    if (achievedpercentage >= 41) and (achievedpercentage <= 60):
                                        recommendation = "Good ! Follow" \
                                                         " the general recommendations to improve further !!"
                                    if achievedpercentage >= 61:
                                        recommendation = "Excellent !"
                                    else:
                                        recommendation = "Needs improvement ! Maturity should be more than 40%. " \
                                                         "Follow the general recommendations to improve !!"
                                elif functionality_data.first().priority == 4:
                                    if (achievedpercentage >= 21) and (achievedpercentage <= 40):
                                        recommendation = "Good ! Follow" \
                                                         " the general recommendations to improve further !!"
                                    if achievedpercentage >= 41:
                                        recommendation = "Excellent !"
                                    else:
                                        recommendation = "Needs improvement ! Maturity should be more than 20%. " \
                                                         "Follow the general recommendations to improve !!"
                                elif functionality_data.first().priority == 5:
                                    if (achievedpercentage >= 1) and (achievedpercentage <= 20):
                                        recommendation = "Good ! Follow" \
                                                         " the general recommendations to improve further !!"
                                    if achievedpercentage >= 21:
                                        recommendation = "Excellent !"
                                    else:
                                        recommendation = "Needs improvement ! Maturity should be more than zero. " \
                                                         "Follow the general recommendations to improve !!"
                                functionality_data.first().achievedlevel = achievedlevel
                                functionality_data.first().recommendation = recommendation
                                functionality_data.first().modifiedby = None
                                db.session.add(functionality_data.first())
                                db.session.commit()
                            except Exception as e:
                                print(e, flush=True)
                                db.session.rollback()
                            finally:
                                db.session.close()
                            func_data = Functionality.query.filter_by(id=functionality_id)
                            for d in func_data:
                                json_data = mergedict({'id': d.id},
                                                      {'name': d.name},
                                                      {'description': d.description},
                                                      {'priority': d.priority},
                                                      {'recommendation': d.recommendation},
                                                      {'retake_assessment_days': d.retake_assessment_days},
                                                      {'area_id': d.area_id},
                                                      {'proj_id': d.proj_id},
                                                      {'assessmentcompletion': str(d.assessmentcompletion)},
                                                      {'achievedpercentage': str(d.achievedpercentage)},
                                                      {'achievedlevel': d.achievedlevel},
                                                      {'creationdatetime': d.creationdatetime},
                                                      {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                      {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                      {'updationdatetime': d.updationdatetime},
                                                      {'createdby': d.createdby},
                                                      {'modifiedby': d.modifiedby})
                                results.append(json_data)
                            functionalitydataafter = results[0]
                            # region call audit trail method
                            try:
                                auditins = Audittrail("FUNCTIONALITY", "UPDATE", str(functionalitydatabefore),
                                                      str(functionalitydataafter),
                                                      None)
                                db.session.add(auditins)
                                db.session.commit()
                            except Exception as e:
                                print(e, flush=True)
                                db.session.rollback()
                            finally:
                                db.session.close()
                            # end region
                            d = Functionality.query.filter_by(id=functionality_id).first()
                            return make_response(jsonify({"assessmentcompletion": str(d.assessmentcompletion),
                                                          "achievedpercentage": str(d.achievedpercentage),
                                                          "achievedlevel": d.achievedlevel,
                                                          "prevassessmentcompletion": str(d.prevassessmentcompletion),
                                                          "prevachievedpercentage": str(
                                                              d.prevachievedpercentage),
                                                          "recommendation": recommendation})), 200
                        else:
                            return make_response(jsonify({"msg": "No Sub-functionality data found!!"})), 404
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500


@reports.route('/api/achievedpercentagebysubfunctionality', methods=['POST'])
def achievedpercentagebysubfunctionality():
    try:
        results = []
        countofnaques = 0
        countofquestionanswered = 0
        scoreachievedforthefunc = 0
        countofquestions = 0
        maxscoreforthefunc = 0
        achievedlevel = ''
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_token = auth_header.split(" ")[1]
        else:
            auth_token = ''
        if auth_token:
            resp = Companyuserdetails.decode_auth_token(auth_token)
            if Companyuserdetails.query.filter_by(empemail=resp).first() is not None:
                if request.method == "POST":
                    res = request.get_json(force=True)
                    projid = res['projectid']
                    area_id = res['area_id']
                    functionality_id = res['functionality_id']
                    subfunc_id = res['subfunc_id']
                    data = Subfunctionality.query.filter_by(id=subfunc_id)
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
                                              {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                              {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                              {'updationdatetime': d.updationdatetime},
                                              {'createdby': d.createdby},
                                              {'modifiedby': d.modifiedby})
                        results.append(json_data)
                    subfunctionalitydatabefore = results[0]
                    results.clear()
                    assessment_data = Assessment.query.filter_by(projectid=projid,
                                                                 area_id=area_id,
                                                                 functionality_id=functionality_id,
                                                                 subfunctionality_id=subfunc_id,
                                                                 assessmentstatus="COMPLETED",
                                                                 employeeassignedstatus=1,
                                                                 active=1)
                    if assessment_data.count() > 0:
                        for data in assessment_data:
                            countofquestions = countofquestions + data.countoftotalquestions
                            cofquesanswdperassessment = QuestionsAnswered.query.filter_by(assignmentid=data.id,
                                                                                          active=1,
                                                                                          applicability=1).count()
                            cofnaquesperassessment = QuestionsAnswered.query.filter_by(assignmentid=data.id,
                                                                                       active=1,
                                                                                       applicability=0).count()
                            countofnaques = countofnaques + cofnaquesperassessment
                            countofquestionanswered = countofquestionanswered + cofquesanswdperassessment
                            scoreachievedforthefunc = scoreachievedforthefunc + data.totalscoreachieved
                            maxscoreforthefunc = maxscoreforthefunc + data.totalmaxscore
                        if countofnaques != 0:
                            countofquestions = countofquestions - countofnaques
                        if countofquestions != 0:
                            assessmentcompletion = ((countofquestionanswered / assessment_data.
                                                     count()) / countofquestions) * 100
                            achievedpercentage = (scoreachievedforthefunc / maxscoreforthefunc) * 100
                        else:
                            assessmentcompletion = 0
                            achievedpercentage = 0
                        try:
                            subfunctionality_data = Subfunctionality.query.filter_by(id=subfunc_id)
                            leveldata = Project.query.filter(Project.id == subfunctionality_data.first().proj_id)
                            if leveldata.first() is not None:
                                for level in leveldata.first().levels:
                                    if (achievedpercentage >= level['RangeFrom']) and (
                                            achievedpercentage <= level['RangeTo']):
                                        achievedlevel = level['LevelName']
                                        break
                            else:
                                achievedlevel = ''
                            prevassessmentcompletion = subfunctionality_data.first().assessmentcompletion
                            if prevassessmentcompletion != assessmentcompletion:
                                subfunctionality_data.first().prevassessmentcompletion = prevassessmentcompletion
                            subfunctionality_data.first().assessmentcompletion = assessmentcompletion
                            prevachievedpercentage = subfunctionality_data.first().achievedpercentage
                            if prevachievedpercentage != achievedpercentage:
                                subfunctionality_data.first().prevachievedpercentage = prevachievedpercentage
                            subfunctionality_data.first().achievedpercentage = achievedpercentage
                            subfunctionality_data.first().achievedlevel = achievedlevel
                            subfunctionality_data.first().modifiedby = None
                            db.session.add(subfunctionality_data.first())
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        subfunc_data = Subfunctionality.query.filter_by(id=subfunc_id)
                        for d in subfunc_data:
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
                                                  {'prevassessmentcompletion': str(d.prevassessmentcompletion)},
                                                  {'prevachievedpercentage': str(d.prevachievedpercentage)},
                                                  {'updationdatetime': d.updationdatetime},
                                                  {'createdby': d.createdby},
                                                  {'modifiedby': d.modifiedby})
                            results.append(json_data)
                        subfunctionalitydataafter = results[0]
                        # region call audit trail method
                        try:
                            auditins = Audittrail("SUBFUNCTIONALITY", "UPDATE", str(subfunctionalitydatabefore),
                                                  str(subfunctionalitydataafter),
                                                  None)
                            db.session.add(auditins)
                            db.session.commit()
                        except Exception as e:
                            print(e, flush=True)
                            db.session.rollback()
                        finally:
                            db.session.close()
                        # end region
                        d = Subfunctionality.query.filter_by(id=subfunc_id).first()
                        return make_response(jsonify({"assessmentcompletion": str(d.assessmentcompletion),
                                                      "achievedpercentage": str(d.achievedpercentage),
                                                      "achievedlevel": d.achievedlevel,
                                                      "prevassessmentcompletion": str(d.prevassessmentcompletion),
                                                      "prevachievedpercentage": str(d.prevachievedpercentage)})), 200
                    else:
                        return make_response(jsonify({"msg": "No Sub-functionality assessment data found!!"})), 404
            else:
                return make_response(jsonify({"msg": resp})), 401
        else:
            return make_response(jsonify({"msg": "Provide a valid auth token."})), 401
    except Exception as e:
        return make_response(jsonify({"msg": str(e)})), 500
