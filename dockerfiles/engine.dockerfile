FROM python:3

# Install proto compiler
RUN apt-get update \
&& apt-get install -y zip
RUN curl -OL https://github.com/google/protobuf/releases/download/v3.2.0/protoc-3.2.0-linux-x86_64.zip
RUN unzip protoc-3.2.0-linux-x86_64.zip -d protoc3

# Mount the repo with the code
ADD . /code
WORKDIR /code

# Generate classes
RUN /protoc3/bin/protoc -I=protobuf --python_out=src protobuf/knapsack.proto

# Install project dependencies
RUN pip install -r requirements.txt

# Set actual working directory
WORKDIR /code/src

RUN ls -al

# Ignite
CMD ["python", "engine.py", "$KAPP_ENGINE_HOST"]