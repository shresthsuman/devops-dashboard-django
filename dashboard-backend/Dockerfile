FROM python:3.6

EXPOSE 8000

WORKDIR /app

#VOLUME "/opt/data"

# Install required RPMs
RUN apt-get update \
  && apt-get -y install libwww-perl libdbi-perl libdbd-mysql-perl libgd-gd2-perl vim mysql-client wait-for-it\
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD requirements.txt /app

# Install required python modules
RUN pip install --no-cache-dir -r /app/requirements.txt

ADD . /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
