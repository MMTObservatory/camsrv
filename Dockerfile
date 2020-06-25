FROM python:latest

MAINTAINER T. E. Pickering "te.pickering@gmail.com"

COPY . .

RUN python -m pip install --upgrade pip
RUN python -m pip install --upgrade tornado
RUN python -m pip install git+https://github.com/MMTObservatory/indiclient.git#egg=indiclient
RUN pip install -e .[all,test]

WORKDIR /camsrv

ENV WFSROOT /camsrv
ENV MATCAMROOT /camsrv
