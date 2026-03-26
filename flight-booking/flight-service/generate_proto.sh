#!/bin/bash

# Generate Python code from proto files
python -m grpc_tools.protoc \
    -I. \
    --python_out=./app \
    --grpc_python_out=./app \
    ./flight_service.proto

echo "Proto files generated successfully!"
