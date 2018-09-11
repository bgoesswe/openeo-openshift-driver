FROM continuumio/miniconda3:latest

RUN conda create -n condaenv -c conda-forge python=3.6 gdal 

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ADD . /usr/src/app

CMD /bin/bash -c "source activate condaenv && python app.py"
