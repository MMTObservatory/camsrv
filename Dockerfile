FROM python:latest

MAINTAINER T. E. Pickering "te.pickering@gmail.com"

COPY . .

RUN pip install -e .[all,test]

WORKDIR /camsrv

ENV WFSROOT /camsrv
ENV MATCAMROOT /camsrv
