#!/usr/bin/env bash
# robot-sim · Ubuntu 实物级仿真启动脚本（占位）
# TODO: 按团队真实技术栈补全——以下为 ROS2 + Gazebo / NVIDIA Isaac Sim 的典型骨架，
#       需替换为实际的环境激活、模型路径与仿真启动命令。

set -e
echo "[robot-sim] Ubuntu 实物级机器人仿真启动（占位脚本）"

# === TODO 1: 环境准备（按真实栈选择）===
# 例：ROS2 + Gazebo
#   source /opt/ros/humble/setup.bash
#   export GAZEBO_MODEL_PATH=$PWD/models:$GAZEBO_MODEL_PATH
# 例：NVIDIA Isaac Sim
#   source ~/.isaac_sim/setup.bash

# === TODO 2: 由设计契约生成 URDF/SDF（已就绪的占位生成器）===
python run_sim.py

# === TODO 3: 加载到仿真器并启动（替换为真实命令）===
# 例：Gazebo
#   gz sim -r output/robot.sdf
# 例：Isaac Sim（Python 入口）
#   isaac-sim python spawn_and_sim.py --urdf output/robot.urdf

echo "[robot-sim] 占位启动完成；请按 TODO 接入真实物理引擎与运动控制器。"
