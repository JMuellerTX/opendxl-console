# Build the application and its dependencies as wheels
FROM python:3.13-slim AS builder

# The OpenDXL Python client. The PyPI release (5.6.0.x) pins msgpack<1.0
# (vulnerable, GHSA-6v7p-g79w-8964) and does not work on current Python
# versions; override with a pip requirement specifier once a fixed release
# is published.
ARG DXL_CLIENT_PIP_SPEC="git+https://github.com/derjochenmueller/opendxl-client-python@epo-legacy"

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . /tmp/build
WORKDIR /tmp/build

# Clean application
RUN python ./clean.py

# Build wheels for the client, the application and their dependencies (in one
# resolver pass so that the client requirement is not taken from PyPI)
RUN pip wheel --no-cache-dir -w /tmp/wheels "${DXL_CLIENT_PIP_SPEC}" .

# Runtime image
FROM python:3.13-slim

VOLUME ["/opt/dxlconsole-config"]

EXPOSE 8443

# Install application package and its dependencies
COPY --from=builder /tmp/wheels /tmp/wheels
RUN pip install --no-cache-dir --no-index --find-links /tmp/wheels dxlconsole \
    && rm -rf /tmp/wheels

################### INSTALLATION END #######################
#
# Run the application.
#
# NOTE: The configuration files for the application must be
#       mapped to the path: /opt/dxlconsole-config
#
# For example, specify a "-v" argument to the run command
# to mount a directory on the host as a data volume:
#
#   -v /host/dir/to/config:/opt/dxlconsole-config
#
CMD ["python", "-m", "dxlconsole", "/opt/dxlconsole-config"]
