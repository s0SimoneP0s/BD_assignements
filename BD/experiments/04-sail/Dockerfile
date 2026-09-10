#ARG PYTHON_VERSION=3.10

#FROM python:${PYTHON_VERSION}-slim

#ARG PYSAIL_VERSION=0.7.1
#ARG PYSPARK_VERSION=4.1.2

#RUN python3 -m pip install --no-cache-dir "pyspark-client==${PYSPARK_VERSION}" 
#RUN python3 -m pip install --no-cache-dir "pysail==${PYSAIL_VERSION}"

#ENTRYPOINT ["/usr/local/bin/sail"]


ARG PYTHON_VERSION=3.10
ARG PYSAIL_VERSION=0.7.1
ARG PYSPARK_VERSION=4.1.2
ARG RUST_VERSION=1.96.0
ARG RUST_PROFILE=release
ARG RUSTFLAGS=""
ARG RELEASE_TAG="v0.7.1"



FROM python:${PYTHON_VERSION}-slim AS builder

ARG RELEASE_TAG
ARG RUST_PROFILE
ARG RUSTFLAGS

ENV RUSTFLAGS="${RUSTFLAGS}"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        gcc \
        libc6-dev \
        protobuf-compiler \
        libprotobuf-dev \
        curl \
        git \
        pkg-config

#RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /tmp/rustup-init && \
#    chmod a+x /tmp/rustup-init && \
#    /tmp/rustup-init -y --no-modify-path --profile default --default-toolchain ${RUST_VERSION}

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

RUN git clone --depth 1 --branch "${RELEASE_TAG}" https://github.com/lakehq/sail.git .

RUN --mount=type=cache,target=/root/.cargo/registry/ \
    --mount=type=cache,target=/root/.cargo/git/ \
    --mount=type=cache,target=/app/target/ \
    RUST_TARGET_SUBDIR=$(case "${RUST_PROFILE}" in \
        dev|test) echo "debug" ;; \
        release|bench) echo "release" ;; \
        *) echo "${RUST_PROFILE}" ;; \
    esac) && \
    CARGO_PROFILE_RELEASE_LTO=false \
    CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
    cargo build -p sail-cli --profile ${RUST_PROFILE} --bins  && \
    cp /app/target/${RUST_TARGET_SUBDIR}/sail /usr/local/bin

#    cargo build -p sail-cli --profile ${RUST_PROFILE} --bins --jobs 1 && \


FROM python:${PYTHON_VERSION}-slim

ARG PYSPARK_VERSION

RUN python3 -m pip install --no-cache-dir "pyspark-client==${PYSPARK_VERSION}"

COPY --from=builder /usr/local/bin/sail /usr/local/bin

ENTRYPOINT ["/usr/local/bin/sail"]
#CMD ["spark", "server", "--ip", "0.0.0.0", "--port", "50051"]
