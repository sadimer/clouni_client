FROM python:3.8-slim
LABEL maintainer="ISP RAS"
WORKDIR /app/

RUN apt update &&\
    apt install python3-pip -y

RUN pip3 install --extra-index-url https://test.pypi.org/simple/ jinja2==3.0.3 grpcio==1.37.1 grpcio-tools==1.37.1 grpc-cotea ansible==2.9.19 \
    openstacksdk==0.46.1 boto3 botocore urllib3 bs4

RUN apt remove python3-pip -y &&\
    apt autoremove -y &&\
    apt clean

EXPOSE 50151
CMD grpc-cotea -p 50151 --host 0.0.0.0