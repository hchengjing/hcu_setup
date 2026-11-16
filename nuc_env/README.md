# NUC environment backup

Captured from the WSL2 Ubuntu 20.04 setup before moving to native Ubuntu 20.04.

- `bashrc_additions.sh` — lines appended to `~/.bashrc` (ROS Noetic, conda, Hik MVS SDK env vars, pixi PATH). Append to the new `~/.bashrc`.
- `condarc` — copy to `~/.condarc`.
- `MVS.desktop` — Hik MVS launcher shortcut (copy to `~/` or `~/.local/share/applications/`).

Upstream UMI-3D (`hku-mars/UMI-3D` @ 0c54c1e) local changes are in
`../umi3d_pixi_ws/upstream_umi3d_cxx17_pcl115.patch`; the pixi files in `../umi3d_pixi_ws/`
go into `UMI-3D/umi_3d_slam_ws/`.

Not in git (copy manually): `~/fyp/bags/nuc_mid360s_custom_test.bag` (103 MB, over GitHub's 100 MB limit).
