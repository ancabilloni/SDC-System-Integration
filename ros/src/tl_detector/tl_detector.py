#!/usr/bin/env python
import rospy
from std_msgs.msg import Int32
from geometry_msgs.msg import PoseStamped, Pose
from styx_msgs.msg import TrafficLightArray, TrafficLight
from styx_msgs.msg import Lane
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from light_classification.tl_classifier import TLClassifier
import tf
import cv2
import math
import numpy as np
import yaml
from  tldetect import predictor
STATE_COUNT_THRESHOLD = 1

class TLDetector(object):
    def __init__(self):
        rospy.init_node('tl_detector')
        p = predictor(modelpath="./FrozenSyam.pb")
        self.predictor = p
        self.pose = None
        self.waypoints = None
        self.camera_image = None
        self.lights = []

        sub1 = rospy.Subscriber('/current_pose', PoseStamped, self.pose_cb)
        sub2 = rospy.Subscriber('/base_waypoints', Lane, self.waypoints_cb)
        self.traffic_light_pos =[[1148.56, 1184.65],

                    [1559.2, 1158.43],

                    [2122.14, 1526.79],

                    [2175.237, 1795.71],

                    [1493.29, 2947.67],

                    [821.96, 2905.8],

                    [161.76, 2303.82],

                    [351.84, 1574.65]]
        '''
        /vehicle/traffic_lights helps you acquire an accurate ground truth data source for the traffic light
        classifier, providing the location and current color state of all traffic lights in the
        simulator. This state can be used to generate classified images or subbed into your solution to
        help you work on another single component of the node. This topic won't be available when
        testing your solution in real life so don't rely on it in the final submission.
        '''
        sub3 = rospy.Subscriber('/vehicle/traffic_lights', TrafficLightArray, self.traffic_cb)
        sub6 = rospy.Subscriber('/image_color', Image, self.image_cb)

        config_string = rospy.get_param("/traffic_light_config")
        self.config = yaml.load(config_string)

        self.upcoming_red_light_pub = rospy.Publisher('/traffic_waypoint', Int32, queue_size=1)

        self.bridge = CvBridge()
        self.light_classifier = TLClassifier()
        self.listener = tf.TransformListener()

        self.state = TrafficLight.UNKNOWN
        self.last_state = TrafficLight.UNKNOWN
        self.last_wp = -1
        self.state_count = 0

        rospy.spin()

    def pose_cb(self, msg):
        self.pose = msg

    def waypoints_cb(self, waypoints):
        self.waypoints = waypoints.waypoints

    def traffic_cb(self, msg):
        self.lights = msg.lights

    def image_cb(self, msg):
        """Identifies red lights in the incoming camera image and publishes the index
            of the waypoint closest to the red light to /traffic_waypoint

        Args:
            msg (Image): image from car-mounted camera

        """
        self.has_image = True
        self.camera_image = msg
        
        # light_wp, state = self.process_traffic_lights()
        cv_image = self.bridge.imgmsg_to_cv2(msg)
        # cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        import uuid

        unique_filename = str(uuid.uuid4())
        
        
        # mesage = "Pred = {} score = {}".format(str(pred),str(1.0))
        # rospy.logwarn(mesage)
        # cv2.imwrite("/home/evotianus/CarND-Capstone/temprun/{}.png".format(unique_filename),np.array(cv_image))
        (pred,skores) = self.predictor.predict(cv_image)
        # img.save("/home/evotianus/CarND-Capstone/temprun/{}.png".format(str(pred)))
        # cv2.imwrite("/home/evotianus/CarND-Capstone/temprun/{}.png".format(unique_filename),(img))
        # mesage = "Pred = {} score = {}".format(str(pred),str(skores))
        # rospy.logwarn(mesage)
        # try:
        #     pred = pred[0]
        # except:
        #     pred = 4
        '''
        Publish upcoming red lights at camera frequency.
        Each predicted state has to occur `STATE_COUNT_THRESHOLD` number
        of times till we start using it. Otherwise the previous stable state is
        used.
        '''
        # carpos = self.get_closest_waypoint(self.pose.pose)
        nearest_tl = float(1000)
        index=None
        for tl in self.traffic_light_pos:
            light_stop_pose = Pose()
            light_stop_pose.position.x = tl[0]
            light_stop_pose.position.y = tl[1]
            
            eucliddist = (tl[0] - self.pose.pose.position.x)*(tl[0] - self.pose.pose.position.x) + (tl[1] - self.pose.pose.position.y)*(tl[1] - self.pose.pose.position.y)
            eucliddist = math.sqrt(eucliddist)
            if eucliddist < nearest_tl:
                nearest_tl = eucliddist
                light_stop_wp = self.get_closest_waypoint(light_stop_pose)
        if(nearest_tl<float(6.0)):
            self.upcoming_red_light_pub.publish(Int32(light_stop_wp))
            rospy.logwarn("Dude I am publishing this TL with ID: ({}) to the publisher ".format(str(light_stop_wp)))
        rospy.logwarn("Distance to nearest TL is around {} m ".format(str(nearest_tl)))
        # distance_to_nearest = None
        # if self.state != state:
        #     self.state_count = 0
        #     self.state = state
        # elif self.state_count >= STATE_COUNT_THRESHOLD:
        #     self.last_state = self.state
        #     light_wp = light_wp if state == TrafficLight.RED else -1
        #     self.last_wp = light_wp
        #     # pred = pred.lower()
        #     if(1 in pred):
        #         # pred = 1
        #         self.upcoming_red_light_pub.publish(Int32(TrafficLight.RED))
        #     if(3 in pred):
        #         # pred = 0
        #         self.upcoming_red_light_pub.publish(Int32(TrafficLight.GREEN))
        #     if(2 in pred):
        #         self.upcoming_red_light_pub.publish(Int32(TrafficLight.YELLOW))
        #     if(len(pred)==0):
        #         self.upcoming_red_light_pub.publish(Int32(TrafficLight.UNKNOWN))


        # else:
        #     self.upcoming_red_light_pub.publish(Int32(self.last_wp))
        # self.state_count += 1

    def get_closest_waypoint(self, pose):
        #from https://github.com/SiliconCar/CarND-Capstone/blob/master/ros/src/tl_detector/tl_detector.py
        """Identifies the closest path waypoint to the given position
            https://en.wikipedia.org/wiki/Closest_pair_of_points_problem
        Args:
            pose (Pose): position to match a waypoint to
        Returns:
            int: index of the closest waypoint in self.waypoints
        """
        if self.waypoints is None:
            return
        #TODO implement
        min_dist = 10000
        min_loc = None

        pos_x = pose.position.x
        pos_y = pose.position.y
        # check all the waypoints to see which one is the closest to our current position
        for i, waypoint in enumerate(self.waypoints):
            wp_x = waypoint.pose.pose.position.x
            wp_y = waypoint.pose.pose.position.y
            dist = math.sqrt((pos_x - wp_x)**2 + (pos_y - wp_y)**2)
            if (dist < min_dist): #we found a closer wp
                min_loc = i     # we store the index of the closest waypoint
                min_dist = dist     # we save the distance of the closest waypoint

        # returns the index of the closest waypoint
        return min_loc


    def project_to_image_plane(self, point_in_world):
        """Project point from 3D world coordinates to 2D camera image location

        Args:
            point_in_world (Point): 3D location of a point in the world

        Returns:
            x (int): x coordinate of target point in image
            y (int): y coordinate of target point in image

        """

        fx = self.config['camera_info']['focal_length_x']
        fy = self.config['camera_info']['focal_length_y']
        image_width = self.config['camera_info']['image_width']
        image_height = self.config['camera_info']['image_height']

        # get transform between pose of camera and world frame
        trans = None
        try:
            now = rospy.Time.now()
            self.listener.waitForTransform("/base_link",
                  "/world", now, rospy.Duration(1.0))
            (trans, rot) = self.listener.lookupTransform("/base_link",
                  "/world", now)

        except (tf.Exception, tf.LookupException, tf.ConnectivityException):
            rospy.logerr("Failed to find camera to map transform")

        #TODO Use tranform and rotation to calculate 2D position of light in image

        x = 0
        y = 0

        return (x, y)

    def get_light_state(self, light):
        """Determines the current color of the traffic light

        Args:
            light (TrafficLight): light to classify

        Returns:
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        if(not self.has_image):
            self.prev_light_loc = None
            return False

        self.camera_image.encoding = "rgb8"
        cv_image = self.bridge.imgmsg_to_cv2(self.camera_image, "bgr8")

        x, y = self.project_to_image_plane(light.pose.pose.position)

        #TODO use light location to zoom in on traffic light in image

        #Get classification
        return self.light_classifier.get_classification(cv_image)

    def process_traffic_lights(self):
        """Finds closest visible traffic light, if one exists, and determines its
            location and color

        Returns:
            int: index of waypoint closes to the upcoming traffic light (-1 if none exists)
            int: ID of traffic light color (specified in styx_msgs/TrafficLight)

        """
        light = None
        light_positions = self.config['light_positions']
        if(self.pose):
            car_position = self.get_closest_waypoint(self.pose.pose)

        #TODO find the closest visible traffic light (if one exists)

        if light:
            state = self.get_light_state(light)
            return light_wp, state
        self.waypoints = None
        return -1, TrafficLight.UNKNOWN

if __name__ == '__main__':
    try:
        TLDetector()
    except rospy.ROSInterruptException:
        rospy.logerr('Could not start traffic node.')
