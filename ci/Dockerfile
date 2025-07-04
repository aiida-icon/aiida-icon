FROM docker.io/aiidateam/aiida-core:latest

RUN apt-get update --yes && \
    apt-get install hatch && \
    hatch self update

ENTRYPOINT ["/bin/bash"]
