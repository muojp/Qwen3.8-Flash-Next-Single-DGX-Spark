"""Check the emitted Docker argv, without a daemon, network, or GPU."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PlainLaunchTests(unittest.TestCase):
    def test_effective_server_argv_opts_out_and_never_restarts(self):
        source = (ROOT / 'start.sh').read_text()
        block = source.split('cat > "$LAUNCH_SCRIPT" <<LAUNCH_EOF\n', 1)[1].split('\nLAUNCH_EOF', 1)[0]
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / 'launch.sh'
            # Expand the same unquoted heredoc as start.sh, then intercept docker.
            subprocess.run(['bash', '-c', 'cat > "$1" <<LAUNCH_EOF\n' + block + '\nLAUNCH_EOF', 'test', str(script)],
                           env={**os.environ, 'CONTAINER_NAME': 'test-single', 'IMAGE': 'test-image',
                                'MODEL_ID': 'test-model', 'CONTAINER_MEM_GIB': '100'}, check=True)
            out = subprocess.check_output(['bash', '-c',
                'docker() { printf "%s\\0" "$@"; }; source "$1"', 'test', str(script)]).decode().split('\0')
        self.assertIn('--restart=no', out)
        for flag in ('VLLM_NO_USAGE_STATS=1', 'DO_NOT_TRACK=1', 'HF_HUB_DISABLE_TELEMETRY=1',
                     'HF_HUB_OFFLINE=1', 'TRANSFORMERS_OFFLINE=1', 'WANDB_DISABLED=true'):
            self.assertIn(flag, out)
            self.assertEqual(out[out.index(flag)-1], '-e')

    def test_no_watchdog_by_default(self):
        source = (ROOT / 'start.sh').read_text()
        block = source.split('if [[ "${MEMWATCH_ENABLED:-0}" == "1" ]]; then', 1)[1].split('info "Loading weights', 1)[0]
        script = 'info() { :; }; bash() { echo WATCHDOG; }; if [[ "${MEMWATCH_ENABLED:-0}" == "1" ]]; then' + block
        result = subprocess.check_output(['bash', '-c', script], env={'PATH': os.defpath}).decode()
        self.assertNotIn('WATCHDOG', result)

class FirstBootTests(unittest.TestCase):
    def test_empty_log_archive_does_not_abort_first_boot(self):
        source = (ROOT / 'start.sh').read_text()
        block = source.split('ls -1t "$SCRIPT_DIR"/logs/archive/', 1)[1].split('if docker inspect', 1)[0]
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / 'logs/archive').mkdir(parents=True)
            result = subprocess.run(['bash', '-c', 'set -euo pipefail\nls -1t "$SCRIPT_DIR"/logs/archive/' + block + '\necho REACHED_LAUNCH'],
                                    env={'PATH': os.defpath, 'SCRIPT_DIR': td}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('REACHED_LAUNCH', result.stdout)

if __name__ == '__main__':
    unittest.main()
