#!/usr/bin/env python

import rospy
from tf import transformations
from std_msgs.msg import Bool
from geometry_msgs.msg import TwistStamped, PoseStamped
from styx_msgs.msg import Lane
from dbw_mkz_msgs.msg import ThrottleCmd, SteeringCmd, BrakeCmd

from math import cos, sin
import numpy as np

from twist_controller import Controller

POINTS_TO_FIT = 10

'''
You can build this node only after you have built (or partially built) the `waypoint_updater` node.

You will subscribe to `/twist_cmd` message which provides the proposed linear and angular velocities.
You can subscribe to any other message that you find important or refer to the document for list
of messages subscribed to by the reference implementation of this node.

One thing to keep in mind while building this node and the `twist_controller` class is the status
of `dbw_enabled`. While in the simulator, its enabled all the time, in the real car, that will
not be the case. This may cause your PID controller to accumulate error because the car could
temporarily be driven by a human instead of your controller.

We have provided two launch files with this node. Vehicle specific values (like vehicle_mass,
wheel_base) etc should not be altered in these files.

We have also provided some reference implementations for PID controller and other utility classes.
You are free to use them or build your own.

Once you have the proposed throttle, brake, and steer values, publish it on the various publishers
that we have created in the `__init__` function.

'''


class DBWNode(object):
    """
    CONTROL SUBSYSTEM

    *** STEP 3 ***

    Actuates the throttle steering and brake to successfully navigate the waypoints with the correct target
    velocity.
    """
    def __init__(self):
        rospy.init_node('dbw_node')

        # variables
        self.current_ego_pose = None  # ego car current position and orientation

        # ROS Server Parameters
        self.vehicle_mass = rospy.get_param('~vehicle_mass', 1736.35)
        # fuel_capacity = rospy.get_param('~fuel_capacity', 13.5)
        # brake_deadband = rospy.get_param('~brake_deadband', .1)
        # decel_limit = rospy.get_param('~decel_limit', -5)
        # accel_limit = rospy.get_param('~accel_limit', 1.)
        self.wheel_radius = rospy.get_param('~wheel_radius', 0.2413)
        self.wheel_base = rospy.get_param('~wheel_base', 2.8498)
        self.steer_ratio = rospy.get_param('~steer_ratio', 14.8)
        self.max_lat_accel = rospy.get_param('~max_lat_accel', 3.)
        self.max_steer_angle = rospy.get_param('~max_steer_angle', 8.)
        self.max_throttle = rospy.get_param('~max_throttle_proportional', 0.8)
        self.max_brake = rospy.get_param('~max_brake_proportional', -0.8)


        # Publishers
        self.steer_pub = rospy.Publisher('/vehicle/steering_cmd', SteeringCmd, queue_size=1)
        self.throttle_pub = rospy.Publisher('/vehicle/throttle_cmd', ThrottleCmd, queue_size=1)
        self.brake_pub = rospy.Publisher('/vehicle/brake_cmd', BrakeCmd, queue_size=1)

        # Subscribers
        # TODO: Subscribe to all the topics you need to
        rospy.Subscriber('/twist_cmd', TwistStamped, self.twist_cb, queue_size=1)
        rospy.Subscriber('/current_velocity', TwistStamped, self.velocity_cb, queue_size=1)
        rospy.Subscriber('/vehicle/dbw_enabled', Bool, self.dbw_enabled_cb, queue_size=1)
        rospy.Subscriber('/final_waypoints', Lane, self.waypoints_cb, queue_size=1)
        rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb, queue_size=1)

        # Subscribed messages
        self.twist_cmd = None
        self.twist_cmd_linear_velocity = None
        self.twist_cmd_angular_velocity = None
        self.velocity = None
        self.current_linear_velocity = None
        self.current_angular_velocity = None
        self.dbw_enabled = False
        self.waypoints = None

        # TODO: Create `TwistController` object
        self.controller = Controller(self.wheel_base, self.steer_ratio, self.max_lat_accel,
                                     self.max_steer_angle)

        self.loop()

    def loop(self):
        """
        Gets predicted throttle, brake, and steering using TwistController.
        """
        # You should only publish the control commands if dbw is enabled
        rate = rospy.Rate(10)  # 10Hz

        while not rospy.is_shutdown():

            data = [self.velocity, self.waypoints, self.current_ego_pose]
            all_available = all([x is not None for x in data])

            if not all_available:
                continue

            if len(self.waypoints) >= POINTS_TO_FIT:
                # print("target_velocity aka self.waypoints[0].twist.twist.linear.x : ", self.waypoints[0].twist.twist.linear.x)  # e.g. 11.1112
                target_velocity = self.waypoints[0].twist.twist.linear.x

                # print("current_linear_velocity aka self.velocity.linear.x : ", self.velocity.linear.x)  # e.g. 0.267761447712
                current_linear_velocity = self.velocity.linear.x

                # Get corrected steering using twist_controller
                cte = self.cte_calc(self.current_ego_pose, self.waypoints)
                steer = self.controller.control(cte, self.dbw_enabled, self.twist_cmd_linear_velocity,
                                                self.twist_cmd_angular_velocity, current_linear_velocity)

                # print("twist_cmd_angular_velocity aka self.twist_cmd.twist.angular.z : ", self.twist_cmd.twist.angular.z)
                # throttle, brake = self.controller.control_speed_based_on_torque(target_velocity,
                #                                                                 current_linear_velocity,
                #                                                                 0.5,
                #                                                                 self.vehicle_mass,
                #                                                                 self.wheel_radius)

                throttle, brake = self.controller.control_velocity_based_on_proportional_throttle_brake(
                                                                                target_velocity,
                                                                                current_linear_velocity,
                                                                                self.max_throttle,
                                                                                self.max_brake)
            else:
                # not enough waypoints so publish heavy break
                rospy.loginfo("Number of waypoint received is : %s", len(self.waypoints))
                throttle, brake, steer = 0, 200, 0

            if self.dbw_enabled:
                self.publish(throttle, brake, steer)
                rospy.loginfo("published throttle : %s, brake : %s, steer : %s", throttle, brake, steer)

            rospy.logwarn("dbw_node.py : throttle %s, brake %s, steer %s adjustments to dbw_node",
                          throttle, brake, steer)

            rate.sleep()

    def publish(self, throttle, brake, steer):
        tcmd = ThrottleCmd()
        tcmd.enable = True
        tcmd.pedal_cmd_type = ThrottleCmd.CMD_PERCENT
        tcmd.pedal_cmd = throttle
        self.throttle_pub.publish(tcmd)

        scmd = SteeringCmd()
        scmd.enable = True
        scmd.steering_wheel_angle_cmd = steer
        self.steer_pub.publish(scmd)

        bcmd = BrakeCmd()
        bcmd.enable = True
        bcmd.pedal_cmd_type = BrakeCmd.CMD_TORQUE
        bcmd.pedal_cmd = brake
        self.brake_pub.publish(bcmd)

    def pose_cb(self, message):
        self.current_ego_pose = message.pose

    def twist_cb(self, message):
        self.twist_cmd = message
        self.twist_cmd_linear_velocity = self.twist_cmd.twist.linear.x
        self.twist_cmd_angular_velocity = self.twist_cmd.twist.angular.z

    def velocity_cb(self, message):
        self.velocity = message.twist
        self.current_linear_velocity = message.twist.linear.x
        self.current_angular_velocity = message.twist.angular.z

    def waypoints_cb(self, message):
        self.waypoints = message.waypoints


    def cte_calc(self, pose, waypoints):
        """
        Calculates the distance from the ego cars current position to the waypoints path.

        See Polynomial fitting - http://blog.mmast.net/least-squares-fitting-numpy-scipy
        """
        #rospy.logwarn("-----")
        x_coords, y_coords = self.transform_waypoints(pose, waypoints, POINTS_TO_FIT)  # Use 10 waypoints
        coefficients = np.polyfit(x_coords, y_coords, 3)  # 3-degree polynomial fit, minimising squared error
        #rospy.logwarn("coefficients : %s", coefficients)  # Curve fits these 4 points
                                                            # See https://en.wikipedia.org/wiki/Curve_fitting
        #distance = np.polyval(coefficients, 1.0)  # polynomial evaluation at 1 results in some steering swerve
        distance = np.polyval(coefficients, 5.0)  # distance between car position and transformed waypoint
        #distance = np.polyval(coefficients, 10.0)  # polynomial evaluation at 10 results in jittery steering
        #rospy.logwarn("distance : %s", distance)
        #rospy.logwarn("-----")

        return distance

    def transform_waypoints(self, pose, waypoints, points_to_use=None):
        """
        Do transformation that sets origin of waypoints to the ego car position, oriented along x-axis and
        returns transformed waypoint co-ordinates.

        See Change of basis | Essence of linear algebra, chapter 9 - https://youtu.be/P2LTAUO1TdA
        """
        x_coords = []  # array to hold transformed waypoint x
        y_coords = []  # array to hold transformed waypoint y

        _, _, yaw = self.get_euler(pose)
        origin_x = pose.position.x
        origin_y = pose.position.y

        if points_to_use is None:
            points_to_use = len(waypoints)

        for i in range(points_to_use):
            shift_x = waypoints[i].pose.pose.position.x - origin_x
            shift_y = waypoints[i].pose.pose.position.y - origin_y

            x = shift_x * cos(0 - yaw) - shift_y * sin(0 - yaw)
            y = shift_x * sin(0 - yaw) + shift_y * cos(0 - yaw)
            #rospy.logwarn("i %s - x_coord : %s", i, x)
            #rospy.logwarn("i %s - y_coord : %s", i, y)

            x_coords.append(x)
            y_coords.append(y)

        return x_coords, y_coords

    def get_euler(self, pose):
        """ Returns roll (x-axis), pitch (y-axis), yaw (z-axis) from a Quaternion.

        See ROS Quaternion Basics for usage - http://wiki.ros.org/Tutorials/Quaternions
        """
        return transformations.euler_from_quaternion(
            [pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w])

    def dbw_enabled_cb(self, message):
        """
        Enabled Self-Driving mode will publish throttle, brake and steer values.
        """
        self.dbw_enabled = bool(message.data)
        if self.dbw_enabled:
            rospy.logwarn("*** ============================= ***")
            rospy.logwarn("*** Self-Driving mode activated ! ***")
            rospy.logwarn("*** ============================= ***")
        else:
            rospy.logwarn("*** =============================== ***")
            rospy.logwarn("*** Manual Driving mode activated ! ***")
            rospy.logwarn("*** =============================== ***")


if __name__ == '__main__':
    DBWNode()
