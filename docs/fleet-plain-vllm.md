# Single-head deployment in ultra-sparkdash

The upstream recipe is preserved as source, but the deployed runtime is one Docker container
whose image entrypoint is `vllm serve`. The fleet uses start.sh / stop.sh, not supervise.sh.
`MEMWATCH_ENABLED=0` is the mirror default; Docker restart is explicitly `no`. No systemd units,
supervisor, maintenance relaunch, heartbeat, or alert script are provisioned to the head.
Startup memory budgeting, PLE offload, cgroup limits and graceful stop are retained. Without the
watchdog there is no automatic low-memory stop; benchmark host memory is monitored externally.

Necessary model support retained: PLE packing/mmap and offload protocol fixes; ModelOpt mixed
precision dispatch; QSA FP8 KV; reduced-vocabulary MTP. These modify engine code but do not add
an external gateway or daemon. Stock checkpoint is Mia-AiLab/Qwen3.8-Flash-Next-NVFP4; the dual
recipe's NVIDIA checkpoint has different quantization and PLE dimensions and is not substituted.

All Python helpers that import engine code run with Docker network=none and telemetry opt-outs.
Download runs with HF telemetry off, but needs network to retrieve weights. Serving has
VLLM_NO_USAGE_STATS=1, DO_NOT_TRACK=1, HF_HUB_DISABLE_TELEMETRY=1, WANDB_DISABLED=true,
HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1. The engine's local /metrics is retained.
These are application opt-outs, not a host egress firewall. No alert webhook is configured.

The existing image was inspected before boot: entrypoint [vllm, serve], digest
sha256:fc120ece0a388cc0aa1caad4a9f1cd92113484ab7ec2fd0efadd62585be05bf8.
vLLM usage_lib reads VLLM_NO_USAGE_STATS / DO_NOT_TRACK; HF constants and _telemetry read
HF_HUB_DISABLE_TELEMETRY and offline settings. Confirm again in the live container after boot.

Provision from the mirror, copying source but excluding systemd/ and scripts/{supervise,
heartbeat,alert,maintenance-relaunch}.sh. Copy the checked-in .env.fleet to .env (contains no credentials). The image digest is pinned.
Only head is provisioned. Run download.sh (includes SHA256 validation) before dgx-model switch.
Do not install the upstream optional services alongside dgx-model.
