FROM reopt/py312

# Install NLR root certs for machines running on NLR's network.
ARG NREL_ROOT_CERT_URL_ROOT=""
RUN set -x && if [ -n "$NREL_ROOT_CERT_URL_ROOT" ]; then curl -fsSLk -o /usr/local/share/ca-certificates/nrel_root.crt "${NREL_ROOT_CERT_URL_ROOT}/nrel_root.pem" && curl -fsSLk -o /usr/local/share/ca-certificates/nrel_xca1.crt "${NREL_ROOT_CERT_URL_ROOT}/nrel_xca1.pem" &&  update-ca-certificates; fi
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

ENV SRC_DIR=/opt/reopt/reo/src
ENV LD_LIBRARY_PATH="/opt/reopt/reo/src:${LD_LIBRARY_PATH}"

# Copy all code
ENV PYTHONDONTWRITEBYTECODE=1
COPY . /opt/reopt

# Install python packages
WORKDIR /opt/reopt
RUN ["pip", "install", "-r", "requirements.txt"]

# Conditionally install EVI-EnLitePy and pydantic (dependency) if EVI-EnLitePy has been cloned via git submodule
RUN if [ -d "/opt/reopt/EVI-EnLitePy" ] && [ "$(ls -A /opt/reopt/EVI-EnLitePy)" ]; then \
    cd /opt/reopt/EVI-EnLitePy && pip install -e .; \
    pip install pydantic; \
fi

EXPOSE 8000
ENTRYPOINT ["/bin/bash", "-c"]
