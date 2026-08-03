FROM julia:1.11.2

# Install NLR root certs for machines running on NLR's network.
ARG NREL_ROOT_CERT_URL_ROOT=""
RUN set -x && if [ -n "$NREL_ROOT_CERT_URL_ROOT" ]; then curl -fsSLk -o /usr/local/share/ca-certificates/nrel_root.crt "${NREL_ROOT_CERT_URL_ROOT}/nrel_root.pem" && curl -fsSLk -o /usr/local/share/ca-certificates/nrel_xca1.crt "${NREL_ROOT_CERT_URL_ROOT}/nrel_xca1.pem" &&  update-ca-certificates; fi
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Use git cli instead of Julia's libgit2, since we're facing SSL issues with it.
RUN apt-get update && apt-get -y install git && rm -rf /var/lib/apt/lists/* /var/lib/dpkg/*-old /var/cache/* /var/log/*
ENV JULIA_PKG_USE_CLI_GIT=true

# Install Julia packages
ENV JULIA_NUM_THREADS=4
ENV XPRESS_JL_SKIP_LIB_CHECK=True

WORKDIR /opt/julia_src
COPY . .
RUN julia --project=/opt/julia_src -e 'import Pkg; Pkg.instantiate();'
RUN julia --project=/opt/julia_src precompile.jl
EXPOSE 8081

CMD ["bash"]
