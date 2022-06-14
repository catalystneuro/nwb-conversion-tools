FROM python:3.8
WORKDIR /usr/src/
ADD . nwb-conversion-tools/
RUN cd nwb-conversion-tools \
  && pip install -e .[full] \
  && pip uninstall -y numpy \
  && pip install numpy==1.21.0  # needed because of a binary incompatability
