FROM docker.io/aiidateam/aiida-core-with-services:latest

USER root
RUN chmod 4755 /init

ENTRYPOINT ["/init", "/bin/bash"]

USER ${SYSTEM_UID}
