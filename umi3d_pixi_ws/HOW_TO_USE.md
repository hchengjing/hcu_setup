# Upstream UMI-3D SLAM in a pixi (RoboStack Noetic) workspace

These files let you rebuild the NUC's pixi workspace for `hku-mars/UMI-3D`. See `docs/NUC_HANDOFF.md` §5 for the background.

```bash
git clone https://github.com/hku-mars/UMI-3D.git ~/UMI-3D
cd ~/UMI-3D
git apply /path/to/hcu_setup/umi3d_pixi_ws/upstream_umi3d_cxx17_pcl115.patch
cp /path/to/hcu_setup/umi3d_pixi_ws/{pixi.toml,pixi.lock,.gitattributes} umi_3d_slam_ws/
cd umi_3d_slam_ws && pixi install && pixi run build
```

The build task in `pixi.toml` expects Sophus built with the pixi toolchain at
`/home/nuc/fyp/deps/Sophus/build-pixi`. Rebuild Sophus that way, or edit the path.
