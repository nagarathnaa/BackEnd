# pull official base image
FROM python:3.8.7-slim-buster as builder

# set work directory
WORKDIR /usr/src/app

# set environment variables 
# PYTHONDONTWRITEBYTECODE : Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED : Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends gcc

# lint
RUN pip install --upgrade pip
RUN pip install flake8
COPY . /usr/src/app/
RUN flake8 --ignore=E501,F401 --exclude=DOEAssessmentApp/DOE_views/project_view.py,DOEAssessmentApp/DOE_views/company_user_details_view.py .

# install python dependencies
COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt

#Stage 2:
# pull official base image
FROM python:3.8.7-slim-buster

ARG user=doe
ARG group=doe
ARG uid=1000
ARG gid=1000

# create directory for the doe user
RUN mkdir -p /home/doe

# create the doe user
#RUN addgroup --system doe && adduser --system doe --group doe
RUN groupadd -g ${gid} ${group} && useradd -u ${uid} -g ${group} -s /bin/sh ${user}

# create the appropriate directories
ENV HOME=/home/doe
ENV APP_HOME=/home/doe/web
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends netcat
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

RUN apt install postgresql-client-common -y && \
    apt-get install postgresql-client -y
# copy project
COPY . $APP_HOME

# chown all the files to the doe user
RUN chown -R doe:doe $APP_HOME

# change to the doe user
USER doe

RUN chmod +x ./run.sh
RUN sed -i -e 's/\r$//' run.sh
ENTRYPOINT ["./run.sh"]
