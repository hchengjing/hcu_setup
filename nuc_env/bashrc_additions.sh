source /opt/ros/noetic/setup.bash

# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/home/nuc/miniforge3/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/home/nuc/miniforge3/etc/profile.d/conda.sh" ]; then
        . "/home/nuc/miniforge3/etc/profile.d/conda.sh"
    else
        export PATH="/home/nuc/miniforge3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

export MVCAM_SDK_PATH=/opt/MVS

export MVCAM_SDK_VERSION=

export MVCAM_COMMON_RUNENV=/opt/MVS/lib

export MVCAM_GENICAM_CLPROTOCOL=/opt/MVS/lib/CLProtocol

export ALLUSERSPROFILE=/opt/MVS/MVFG
export LD_LIBRARY_PATH=/opt/MVS/lib/64:/opt/MVS/lib/32:$LD_LIBRARY_PATH

export PATH="/home/nuc/.pixi/bin:$PATH"
