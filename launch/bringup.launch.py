# Copyright 2026 Robby
# SPDX-License-Identifier: Apache-2.0
"""Run one wheel-driven ROSMASTER X3 in Gazebo Jetty."""
import os
import math
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import xacro


def setup(context):
    share = get_package_share_directory('rosmaster_x3_jetty')
    value = lambda key: LaunchConfiguration(key).perform(context)
    work = tempfile.mkdtemp(prefix='rosmaster_x3_jetty_')
    robot_path = os.path.join(share, 'urdf', 'robots', 'rosmaster_x3.urdf.xacro')
    description = xacro.process_file(robot_path).toxml()
    urdf_file = os.path.join(work, 'robot.urdf')
    with open(urdf_file, 'w') as stream:
        stream.write(description)
    converted = subprocess.run(['gz', 'sdf', '-p', urdf_file], check=True,
                               capture_output=True, text=True)
    sdf = ET.fromstring(converted.stdout)
    model = sdf.find('model')
    model.set('name', 'rosmaster_x3')
    # Match the official Gazebo MecanumDrive example. Directions are expressed
    # in the chassis frame, so wheel rotation does not rotate the friction axis.
    ET.register_namespace('gz', 'http://gazebosim.org/schema')
    # Fixed-joint reduction merges base_link into base_footprint in this URDF.
    # DART needs the name of the surviving physical body, not an eliminated frame.
    chassis = model.find("joint[@name='front_left_wheel_joint']/parent").text
    for side, direction in [('front_left', '1 -1 0'), ('front_right', '1 1 0'),
                            ('back_left', '1 1 0'), ('back_right', '1 -1 0')]:
        collision = model.find(f"link[@name='{side}_wheel_link']/collision")
        if collision is None:
            raise RuntimeError('Missing wheel collision: ' + side)
        old = collision.find('surface')
        if old is not None:
            collision.remove(old)
        ode = ET.SubElement(ET.SubElement(ET.SubElement(collision, 'surface'), 'friction'), 'ode')
        ET.SubElement(ode, 'mu').text = '1.0'
        ET.SubElement(ode, 'mu2').text = '0.0'
        ET.SubElement(ode, 'fdir1', {'{http://gazebosim.org/schema}expressed_in': chassis}).text = direction
    drive = ET.SubElement(model, 'plugin', filename='gz-sim-mecanum-drive-system',
                          name='gz::sim::systems::MecanumDrive')
    params = {
        'front_left_joint': 'front_left_wheel_joint', 'front_right_joint': 'front_right_wheel_joint',
        'back_left_joint': 'back_left_wheel_joint', 'back_right_joint': 'back_right_wheel_joint',
        'wheel_separation': '0.149', 'wheelbase': '0.16', 'wheel_radius': '0.0325',
        'topic': '/cmd_vel', 'odom_topic': '/odom', 'tf_topic': '/tf',
        'frame_id': 'odom', 'child_frame_id': 'base_footprint', 'odom_publish_frequency': '50',
    }
    for key, text in params.items():
        ET.SubElement(drive, key).text = text
    joints = ET.SubElement(model, 'plugin', filename='gz-sim-joint-state-publisher-system',
                           name='gz::sim::systems::JointStatePublisher')
    ET.SubElement(joints, 'topic').text = '/joint_states'
    for side in ['front_left', 'front_right', 'back_left', 'back_right']:
        ET.SubElement(joints, 'joint_name').text = side + '_wheel_joint'
    sdf_file = os.path.join(work, 'robot.sdf')
    ET.ElementTree(sdf).write(sdf_file, encoding='unicode', xml_declaration=True)
    world_path = value('world')
    if world_path.endswith('.sdf'):
        world_xml = xacro.process_file(world_path, mappings={'headless': 'false'}).toxml()
        world_path = os.path.join(work, 'world.sdf')
        with open(world_path, 'w') as stream:
            stream.write(world_xml)
    args = '-r -v 2 ' + ('-s ' if value('headless').lower() == 'true' else '') + world_path
    if value('headless').lower() != 'true':
        x, y = float(value('x')), float(value('y'))
        pose = f'{x+4.0} {y-4.0} 3.0 0 {math.atan2(2.88, math.hypot(2.5,4.0))} {math.atan2(4.0,-2.5)}'
        with open(os.path.join(share, 'config', 'gui.config')) as stream:
            gui_config = stream.read().replace('_CAMERA_POSE_', pose)
        gui_file = os.path.join(work, 'gui.config')
        with open(gui_file, 'w') as stream:
            stream.write(gui_config)
        args += ' --gui-config ' + gui_file
    gz_share = get_package_share_directory('ros_gz_sim')
    return [
        RegisterEventHandler(OnShutdown(on_shutdown=[OpaqueFunction(
            function=lambda context: shutil.rmtree(work, ignore_errors=True) or [])])),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(
            os.path.join(gz_share, 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': args}.items()),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': ParameterValue(description, value_type=str),
                          'use_sim_time': True}], output='screen'),
        Node(package='ros_gz_sim', executable='create', arguments=[
            '-file', sdf_file, '-name', 'rosmaster_x3', '-x', value('x'),
            '-y', value('y'), '-z', '0.04', '-Y', value('yaw')], output='screen'),
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             parameters=[{'config_file': os.path.join(share, 'config', 'bridge.yaml'),
                          'use_sim_time': True}], output='screen'),
    ]


def generate_launch_description():
    share = get_package_share_directory('rosmaster_x3_jetty')
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=os.path.join(share, 'worlds', 'depot.sdf')),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('x', default_value='-8.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        OpaqueFunction(function=setup),
    ])
