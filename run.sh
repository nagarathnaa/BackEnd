#!/bin/sh

if [ `ls migrations/ | wc -l` -gt 1 ] 
then
    ls migrations
    echo "upgrade"
    python3 manage.py db migrate; python3 manage.py db upgrade
    
else
    rm -rf migrations
    #testing database connection
    #conn=1
    #while [ $conn -ne 0 ]
    #do
	    #echo $conn
	    #pg_isready -d dev_ops_app -h doe-postgres -p 5432 -U postgres
	    #conn=$?
	    #echo $conn
    #done

    python3 manage.py db init; python3 manage.py db migrate; python3 manage.py db upgrade 
    PGPASSWORD=D3v0p5En@bleR psql -h doe-postgres -U postgres -d dev_ops_app -f rbacBackup
    PGPASSWORD=D3v0p5En@bleR psql -h doe-postgres -U postgres -d dev_ops_app -f RoleBackup 
    PGPASSWORD=D3v0p5En@bleR psql -h doe-postgres -U postgres -d dev_ops_app -f notificationBackup 
    python3 create_user_admin_to_login_into_DOE.py

fi   

gunicorn --bind=0.0.0.0:5000 wsgi:app --workers=3 --threads=3 --timeout=900