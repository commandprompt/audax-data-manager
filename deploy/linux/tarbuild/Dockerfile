FROM ubuntu:20.04 AS build-base

ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

USER root
ENV HOME=/root
WORKDIR /root
SHELL ["/bin/bash", "-c"]

ARG PYVER="3.11.15"

RUN apt-get update && apt-get install -y wget gcc make zlib1g-dev libssl-dev \
    libffi-dev libsqlite3-dev liblzma-dev

RUN wget https://www.python.org/ftp/python/$PYVER/Python-$PYVER.tgz && \
    tar -zxvf Python-$PYVER.tgz && \
    cd Python-$PYVER && \
    ./configure --enable-shared && \
    make && \
    make install

RUN rm Python-$PYVER.tgz
RUN rm -r Python-$PYVER/

RUN strip --strip-unneeded /usr/local/lib/libpython3.11.so.1.0

RUN apt-get update && apt-get install -y build-essential

RUN pip3 install setuptools-rust

ARG NFPM_VERSION="2.47.0"
ARG NFPM_SHA256="0660ca602b2d2d2ae4781a06c692b3eeb9d437ffea05b831d76e41f4a3188783"
RUN wget -q -O /tmp/nfpm.tar.gz \
        "https://github.com/goreleaser/nfpm/releases/download/v${NFPM_VERSION}/nfpm_${NFPM_VERSION}_Linux_x86_64.tar.gz" && \
    echo "${NFPM_SHA256}  /tmp/nfpm.tar.gz" | sha256sum -c - && \
    tar -xzf /tmp/nfpm.tar.gz -C /usr/local/bin nfpm && \
    rm /tmp/nfpm.tar.gz

FROM ubuntu:20.04

ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

USER root

ENV REPO="https://github.com/commandprompt/audax-data-manager"
ENV BRANCH="dev"
ENV VERSION=""
ENV HOME=/root
ENV LD_LIBRARY_PATH=/usr/local/lib

WORKDIR /root
SHELL ["/bin/bash", "-c"]

COPY --from=build-base /usr/local /usr/local
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates curl npm gnupg patchelf libpq-dev file binutils build-essential

RUN mkdir -p /etc/apt/keyrings && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
RUN echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list

RUN apt-get update && apt-get install -y --no-install-recommends nodejs

RUN apt autoremove -y

COPY entrypoint.sh $HOME

ENTRYPOINT ["/root/entrypoint.sh"]