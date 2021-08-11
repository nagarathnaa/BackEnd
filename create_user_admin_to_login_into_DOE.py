from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from werkzeug.security import generate_password_hash
from DOEAssessmentApp import db

try:
    checkifuseradminexists = Companyuserdetails.query.filter(Companyuserdetails.empname == "admin").one_or_none()
    if checkifuseradminexists is None:
        add_user_admin = Companyuserdetails("admin1", "admin", "admin", "admin@testmail.com",
                                            generate_password_hash("admin"), 1, None)
        db.session.add(add_user_admin)
        db.session.commit()
        print("User admin added with password admin successfully !!", flush=True)
    else:
        print("User admin already exists !!", flush=True)
except Exception as e:
    print(e)

