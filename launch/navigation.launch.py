# Copyright 2026 Robby
# SPDX-License-Identifier: Apache-2.0
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('rosmaster_x3_jetty')
    nav2 = get_package_share_directory('nav2_bringup')
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=os.path.join(share, 'maps', 'depot.yaml')),
        DeclareLaunchArgument('params_file', default_value=os.path.join(share, 'config', 'nav2.yaml')),
        DeclareLaunchArgument('use_rviz', default_value='true'),
        DeclareLaunchArgument('use_composition', default_value='true'),
        DeclareLaunchArgument('use_keepout_zones', default_value='false'),
        DeclareLaunchArgument('use_speed_zones', default_value='false'),
        DeclareLaunchArgument('keepout_mask', default_value=os.path.join(share, 'maps', 'keepout.yaml')),
        DeclareLaunchArgument('speed_mask', default_value=os.path.join(share, 'maps', 'speed.yaml')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'bringup_launch.py')),
            launch_arguments={
                'map': LaunchConfiguration('map'), 'params_file': LaunchConfiguration('params_file'),
                'use_sim_time': 'true', 'use_composition': LaunchConfiguration('use_composition'), 'autostart': 'true',
                'use_keepout_zones': LaunchConfiguration('use_keepout_zones'),
                'use_speed_zones': LaunchConfiguration('use_speed_zones'),
                'keepout_mask': LaunchConfiguration('keepout_mask'),
                'speed_mask': LaunchConfiguration('speed_mask'),
            }.items()),
        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', os.path.join(share, 'rviz', 'navigation.rviz')],
             parameters=[{'use_sim_time': True}], condition=IfCondition(LaunchConfiguration('use_rviz'))),
    ])
