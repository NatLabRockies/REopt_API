FROM public.ecr.aws/docker/library/ruby:4.0-trixie

# Install NLR root certs for machines running on NLR's network.
ARG NREL_ROOT_CERT_URL_ROOT=""
RUN set -x && if [ -n "$NREL_ROOT_CERT_URL_ROOT" ]; then curl -fsSLk -o /usr/local/share/ca-certificates/nrel_root.crt "${NREL_ROOT_CERT_URL_ROOT}/nrel_root.pem" && curl -fsSLk -o /usr/local/share/ca-certificates/nrel_xca1.crt "${NREL_ROOT_CERT_URL_ROOT}/nrel_xca1.pem" && update-ca-certificates; fi

# Postgresql
ARG POSTGRESQL_MAJOR_VERSION=18
RUN set -x && \
  distro=$(. /etc/os-release && echo "$VERSION_CODENAME") && \
  curl -fsSL -o /usr/share/keyrings/pgdg.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc && \
  echo "deb [signed-by=/usr/share/keyrings/pgdg.asc] http://apt.postgresql.org/pub/repos/apt/ ${distro}-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
  apt-get update && \
  apt-get -y --no-install-recommends install "postgresql-client-${POSTGRESQL_MAJOR_VERSION}" rclone zstd && \
  rm -rf /var/lib/apt/lists/* /var/lib/dpkg/*-old /var/cache/* /var/log/*

ARG TARGETARCH

# Config templates.
ARG GOMPLATE_VERSION=3.11.8
RUN curl -fsSL -o /usr/local/bin/gomplate "https://github.com/hairyhenderson/gomplate/releases/download/v${GOMPLATE_VERSION}/gomplate_linux-${TARGETARCH}" && \
  chmod +x /usr/local/bin/gomplate

WORKDIR /app/db-syncer

# Install gems
COPY ./db-syncer/Gemfile ./db-syncer/Gemfile.lock /app/db-syncer/
ARG BUNDLE_FROZEN="true"
ENV BUNDLE_FROZEN=$BUNDLE_FROZEN
RUN bundle install

# Copy the rest of the app.
COPY ./db-syncer /app/db-syncer
COPY ./config/vault_secrets.json.tmpl /app/config/
