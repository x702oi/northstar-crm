ARG FRAPPE_BRANCH=version-16
ARG FRAPPE_IMAGE_PREFIX=ghcr.io/frappe

FROM ${FRAPPE_IMAGE_PREFIX}/build:${FRAPPE_BRANCH} AS builder

ARG FRAPPE_BRANCH=version-16
ARG FRAPPE_PATH=https://github.com/frappe/frappe

USER frappe

RUN bench init \
    --frappe-branch="${FRAPPE_BRANCH}" \
    --frappe-path="${FRAPPE_PATH}" \
    --no-procfile \
    --no-backups \
    --skip-redis-config-generation \
    --verbose \
    /home/frappe/frappe-bench

COPY --chown=frappe:frappe pyproject.toml README.md license.txt MANIFEST.in /tmp/northstar_crm/
COPY --chown=frappe:frappe northstar_crm /tmp/northstar_crm/northstar_crm

RUN cd /home/frappe/frappe-bench && \
    cp -a /tmp/northstar_crm apps/northstar_crm && \
    ./env/bin/pip install --no-cache-dir -e apps/northstar_crm && \
    if ! grep -Fxq northstar_crm sites/apps.txt; then printf '%s\n' northstar_crm >> sites/apps.txt; fi && \
    bench build --app northstar_crm && \
    echo '{}' > sites/common_site_config.json && \
    find apps -mindepth 1 -path '*/.git' -prune -exec rm -rf {} +

FROM ${FRAPPE_IMAGE_PREFIX}/base:${FRAPPE_BRANCH}

USER frappe

COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench /home/frappe/frappe-bench

WORKDIR /home/frappe/frappe-bench

RUN cp -r sites/assets assets && rm -rf sites/assets

VOLUME ["/home/frappe/frappe-bench/sites", "/home/frappe/frappe-bench/logs"]

USER root

COPY deploy/azure-container-apps/main-entrypoint.sh /usr/local/bin/entrypoint.sh
COPY deploy/azure-container-apps/start.sh /usr/local/bin/start.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh /usr/local/bin/start.sh

USER frappe

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["start.sh"]
