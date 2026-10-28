#!/usr/bin/env python3
"""Run in laptop Ubuntu/WSL. Copy selected sources; never delete/overwrite a destination."""
import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.vscode',
             '.idea', 'build', 'devel', 'install', 'log', 'logs', 'datasets',
             'output', 'outputs', 'data_collection.egg-info'}
SKIP_FILES = ['*.bag', '*.bag.active', '*.pyc', '*.o', '*.a', '*.so', '*.so.*',
              'CMakeCache.txt', '.env']

def ignored(directory, names):
    return [n for n in names if n in SKIP_DIRS or any(fnmatch.fnmatch(n, p) for p in SKIP_FILES)]

def git_info(source):
    result = {}
    for label, args in [('commit', ['rev-parse', 'HEAD']),
                        ('status', ['status', '--short'])]:
        run = subprocess.run(['git', '-C', str(source)] + args, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result[label] = run.stdout.strip() if run.returncode == 0 else 'unavailable'
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=Path.home() / 'fyp/hcu_setup')
    parser.add_argument('--tests', type=Path,
                        default=Path('/mnt/c/Users/haoch/Projects/fyp_tests'))
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    home = Path.home()
    umi = home / 'fyp/UMI-3D'
    src = umi / 'umi_3d_slam_ws/src'
    dest = args.destination.expanduser().resolve()
    sources = [
        (home / 'catkin_ws/src/inspire_gripper', 'ros_ws/src/inspire_gripper'),
        (src / 'umi_3d_slam', 'ros_ws/src/umi_3d_slam'),
        (src / 'livox_ros_driver', 'ros_ws/src/livox_ros_driver'),
        (src / 'livox_ros_driver2', 'ros_ws/src/livox_ros_driver2'),
        (src / 'rpg_vikit-master', 'ros_ws/src/rpg_vikit-master'),
        (src / 'Livox-SDK2', 'third_party/Livox-SDK2'),
        (home / 'Sophus', 'third_party/Sophus'),
        (args.tests.expanduser().resolve(), 'hardware_tests'),
    ]
    if dest.exists():
        sys.exit('STOP: destination already exists; nothing changed: ' + str(dest))
    missing = [str(p) for p, _ in sources if not p.is_dir()]
    if missing:
        sys.exit('STOP: required source folders not found; nothing changed:\n' + '\n'.join(missing))
    for source, relative in sources:
        source = source.resolve()
        if source == dest or source in dest.parents or dest in source.parents:
            sys.exit('STOP: destination overlaps a source: ' + str(source))
        print(str(source) + ' -> ' + relative)
    # Do not copy nonportable system or external symlinks silently.
    unsafe = []
    for source, _ in sources:
        for directory, dirs, files in __import__('os').walk(str(source)):
            dirs[:] = [d for d in dirs if d not in ignored(directory, dirs)]
            for name in dirs + [f for f in files if f not in ignored(directory, files)]:
                path = Path(directory) / name
                if path.is_symlink():
                    target = path.resolve()
                    if not target.exists() or (target != source.resolve() and source.resolve() not in target.parents):
                        unsafe.append(str(path) + ' -> ' + str(target))
    if unsafe:
        sys.exit('STOP: external/broken source symlinks need review; nothing changed:\n' + '\n'.join(unsafe))
    if args.dry_run:
        print('\nDry run passed. No files changed. Run again without --dry-run to assemble.')
        return
    dest.mkdir(parents=True)
    provenance = []
    for source, relative in sources:
        shutil.copytree(str(source), str(dest / relative), ignore=ignored, symlinks=True)
        provenance.append({'source': str(source), 'destination': relative,
                           'git': git_info(source)})
    docs = dest / 'docs'
    docs.mkdir()
    # Preserve the upstream root license and identification alongside retained packages.
    upstream = docs / 'upstream_UMI-3D'
    upstream.mkdir()
    for name in ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING', 'NOTICE', 'README.md']:
        if (umi / name).is_file():
            shutil.copy2(str(umi / name), str(upstream / name))
    for name in ['README_FYP_UMI3D_HANDOFF.md', 'FYP_TODO.md']:
        note = Path(__file__).resolve().parent / name
        if note.is_file():
            shutil.copy2(str(note), str(docs / name))
    shutil.copy2(str(Path(__file__).resolve()), str(docs / 'assemble_hcu_setup.py'))
    (dest / '.gitignore').write_text('''**/build/
**/devel/
**/install/
**/output/
**/outputs/
**/logs/
**/.venv/
**/__pycache__/
**/*.egg-info/
datasets/
*.bag
*.bag.active
*.pyc
.env
''', encoding='utf-8')
    (dest / 'README.md').write_text('''# HCU setup

Selected source snapshot for Haoch's portable ASUS NUC UMI-3D system.
Assembled from the working laptop sources; source copying is not a fresh build or hardware test.

## Layout

- `ros_ws/src/inspire_gripper`: existing custom ROS gripper wrapper.
- `ros_ws/src/umi_3d_slam`: UMI mapping source, local launch files and configuration.
- `ros_ws/src/livox_ros_driver`: retained because UMI compiles against its CustomMsg.
- `ros_ws/src/livox_ros_driver2`: MID-360S acquisition driver and configuration.
- `ros_ws/src/rpg_vikit-master`: Vikit packages required by the mapping build.
- `third_party/Livox-SDK2`: Driver2 SDK source; deliberately outside Catkin package discovery.
- `third_party/Sophus`: laptop Sophus source snapshot.
- `hardware_tests`: custom Windows/Linux peripheral tests and separate calibration tooling.
- `docs`: source provenance, copied-file hashes, handoff, and upstream attribution.

## Existing gripper interface

`/gripper/command` (`std_msgs/Int32`) writes position register 10 after clamping to 0–1000.
`/gripper/position` (`std_msgs/Int32`) publishes register 61 reads at a target 10 Hz.
The existing code hardcodes `/dev/ttyUSB0`, 115200 baud, ID 1, and PyModbus `slave=`.
Runtime validation and portable configuration are still required on the NUC.
Several hardware test files perform movement at module scope: inspect rather than import/run casually.

## Build/deployment status

Target dependency baseline: Ubuntu 20.04 and ROS Noetic. UMI requires Eigen, PCL,
OpenCV, Sophus, Boost thread and its Catkin dependencies. Its CMake also requests
`eigen_conversions`, which the supplied package.xml does not declare.
SDKs must be built/installed deliberately before dependent ROS packages.
Retain the older Livox SDK source inside its driver if present; do not replace it with SDK2.
Check driver build files for any paths that assumed SDK2 lived in the old workspace.
The mapping build uses `-march=native`, so rebuild on the target NUC.

No build/devel/install directories, inherited Git metadata, recordings or root training
pipeline are copied. Package source and existing configuration are preserved without refactoring.
Regenerate the Catkin workspace top-level CMakeLists.txt on the target.
The gripper Python installation rule and dependency/version declarations still need review.
The separate calibration tooling targets Python 3.12; keep it isolated from Noetic Python.

Before publishing, review the file inventory and licenses, confirm the MID360s JSON and
minimal mapping launch exist, then initialize a new Git repository in this folder.
Do not delete or alter the working source workspaces or the remote repository during assembly.
''', encoding='utf-8')
    hashes = {}
    for file in sorted(dest.rglob('*')):
        if file.is_file() and not file.is_symlink():
            hashes[file.relative_to(dest).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest = {'assembled_at_utc': datetime.now(timezone.utc).isoformat(),
                'sources': provenance, 'sha256': hashes,
                'notes': 'Snapshot only. Manifest does not hash itself. No build or hardware run.'}
    (docs / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('\nAssembled: ' + str(dest))
    print('Files hashed: ' + str(len(hashes)))
    for required in ['ros_ws/src/inspire_gripper/scripts/gripper_node.py',
                     'ros_ws/src/livox_ros_driver2/config/MID360s_config.json',
                     'ros_ws/src/umi_3d_slam/launch/mapping_mid360_180_min.launch']:
        print(('FOUND ' if (dest / required).is_file() else 'MISSING - REVIEW ') + required)
    print('Original folders unchanged. No Git commands changed history or uploaded files.')

if __name__ == '__main__':
    main()
