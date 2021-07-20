from DOEAssessmentApp.DOE_models.company_user_details_model import Companyuserdetails
from werkzeug.security import generate_password_hash
from DOEAssessmentApp import db

try:
    add_user_admin = Companyuserdetails("1", "admin", "admin", "admin@testmail.com", generate_password_hash("admin"), 0,
                                        None)
    db.session.add(add_user_admin)
    db.session.commit()

    print("User admin added with password admin successfully !!")
except Exception as e:
    print(e)

