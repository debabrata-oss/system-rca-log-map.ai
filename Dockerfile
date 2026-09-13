FROM python:3.12-slim AS builder

WORKDIR /build
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src/ src/
RUN pip install --no-cache-dir .


FROM curlimages/curl:8.10.1 AS kubectl-fetch

ARG KUBECTL_VERSION=v1.31.2
USER root
RUN ARCH="$(uname -m)" \
    && case "$ARCH" in x86_64) ARCH=amd64 ;; aarch64) ARCH=arm64 ;; esac \
    && BASE_URL="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${ARCH}" \
    && curl -fsSLo /tmp/kubectl "${BASE_URL}/kubectl" \
    && curl -fsSLo /tmp/kubectl.sha256 "${BASE_URL}/kubectl.sha256" \
    && echo "$(cat /tmp/kubectl.sha256)  /tmp/kubectl" | sha256sum -c - \
    && chmod +x /tmp/kubectl


FROM python:3.12-slim AS runtime

RUN groupadd --gid 1000 rca && useradd --uid 1000 --gid rca --create-home --shell /usr/sbin/nologin rca

COPY --from=builder /opt/venv /opt/venv
COPY --from=kubectl-fetch /tmp/kubectl /usr/local/bin/kubectl
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
RUN mkdir -p logs reports /home/rca/.ssh \
    && chown -R rca:rca /app /home/rca/.ssh \
    && chmod 700 /home/rca/.ssh

USER rca

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=3)" || exit 1

CMD ["rca-web"]
