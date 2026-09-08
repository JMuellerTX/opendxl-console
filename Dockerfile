# Build the application and its dependencies as wheels
FROM python:3.13-slim AS builder

# The OpenDXL Python client. The PyPI release (5.6.0.x) pins msgpack<1.0
# (vulnerable, GHSA-6v7p-g79w-8964) and does not work on current Python
# versions; override with a pip requirement specifier once a fixed release
# is published.
ARG DXL_CLIENT_PIP_SPEC="git+https://github.com/JMuellerTX/opendxl-client-python@epo-legacy"

# The dxlbootstrap this application depends on. The PyPI release imports
# pkg_resources, which setuptools 82 dropped and a Python >= 3.12 virtual
# environment no longer provides, so the console cannot even be imported; the
# fork uses importlib.resources instead.
ARG DXL_BOOTSTRAP_PIP_SPEC="git+https://github.com/JMuellerTX/opendxl-bootstrap-python@master"

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
RUN pip wheel --no-cache-dir -w /tmp/wheels "${DXL_CLIENT_PIP_SPEC}" "${DXL_BOOTSTRAP_PIP_SPEC}" .

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
# Run the console as an unprivileged user, the same way it already runs inside
# the broker image (startup_as_root.sh hands over with runuser). Certificate
# signing writes a serial file next to the CA (openssl -CAcreateserial), so a
# host directory mounted at /opt/dxlconsole-config has to be writable by this
# user - uid 10001, not just readable.
RUN useradd --system --create-home --shell /usr/sbin/nologin --uid 10001 dxl \
    && mkdir -p /opt/dxlconsole-config \
    && chown dxl:dxl /opt/dxlconsole-config
USER dxl

CMD ["python", "-m", "dxlconsole", "/opt/dxlconsole-config"]
