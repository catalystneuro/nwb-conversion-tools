FROM python:3.8  # Cannot support 3.9 due to numpy conflict and compatibility issue
WORKDIR /usr/src/
ADD . nwb-conversion-tools/
RUN cd nwb-conversion-tools \
  && pip install -e .[full]
