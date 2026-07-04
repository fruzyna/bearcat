FROM mcr.microsoft.com/devcontainers/python:1-3.12

RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | gpg --dearmor | tee /etc/apt/keyrings/yarn-archive-keyring.gpg > /dev/null
RUN echo "deb [signed-by=/etc/apt/keyrings/yarn-archive-keyring.gpg] https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install libportaudio2