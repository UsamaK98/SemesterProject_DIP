import cv2
import mediapipe as mp
import pyautogui
import math
from enum import IntEnum
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from google.protobuf.json_format import MessageToDict
import json
import numpy as np

# import screen_brightness_control as sbcontrol

pyautogui.FAILSAFE = False
mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands

# Gesture Encodings 
class Gest(IntEnum):
    # Binary Encoded
    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16    
    PALM = 31
    
    # Extra Mappings
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36

# Multi-handedness Labels
class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

# HandRecog class methods:
# ------------------------
# Convert Mediapipe Landmarks to recognizable Gestures. The get_signed_dist, get_dist, and get_dz 
# are methods that calculate distances between two points in different ways. They use the detected 
# landmarks' x, y, and z coordinates to find distances, which helps in gesture recognition.
class HandRecog:
    
    def __init__(self, hand_label):
        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label
    
    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist*sign
    
    def get_dist(self, point):
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist
    
    def get_dz(self,point):
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)
    
    # set_finger_state:
    # This method calculates the finger state (open or closed) based on the distances between
    # certain landmarks. For each finger, the distance ratio between two sets of landmarks is
    # calculated, and if the ratio exceeds a threshold, the finger is considered open. The
    # binary representation of open fingers is stored in the 'self.finger' variable.
    # ------------
    # Function to find Gesture Encoding using current finger_state.
    # Finger_state: 1 if finger is open, else 0
    def set_finger_state(self):
        if self.hand_result == None:
            return

        points = [[8,5,0],[12,9,0],[16,13,0],[20,17,0]]
        self.finger = 0
        self.finger = self.finger | 0 #thumb
        for idx,point in enumerate(points):
            
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])
            
            try:
                ratio = round(dist/dist2,1)
            except:
                ratio = round(dist1/0.01,1)

            self.finger = self.finger << 1
            if ratio > 0.5 :
                self.finger = self.finger | 1
    
    # get_gesture:
    # This method identifies the gesture based on the finger states and some additional
    # conditions. Depending on the finger states and distances between certain landmarks,
    # it classifies gestures such as PINCH_MAJOR, PINCH_MINOR, V_GEST, and TWO_FINGER_CLOSED.
    # The method also handles fluctuations due to noise by maintaining a frame count for
    # consistent gestures.
    def get_gesture(self):
        if self.hand_result == None:
            return Gest.PALM

        current_gesture = Gest.PALM
        if self.finger in [Gest.LAST3,Gest.LAST4] and self.get_dist([8,4]) < 0.05:
            if self.hand_label == HLabel.MINOR :
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        elif Gest.FIRST2 == self.finger :
            point = [[8,12],[5,9]]
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1/dist2
            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8,12]) < 0.1:
                    current_gesture =  Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture =  Gest.MID
            
        else:
            current_gesture =  self.finger
        
        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0

        self.prev_gesture = current_gesture

        if self.frame_count > 4 :
            self.ori_gesture = current_gesture
        return self.ori_gesture



# Controller class: Executes commands according to detected gestures
# --------------------------
class Controller:
    tx_old = 0
    ty_old = 0
    trial = True
    flag = False
    grabflag = False
    pinchmajorflag = False
    pinchminorflag = False
    pinchstartxcoord = None
    pinchstartycoord = None
    pinchdirectionflag = None
    prevpinchlv = 0
    pinchlv = 0
    framecount = 0
    prev_hand = None
    pinch_threshold = 0.3

    # getpinchylv and getpinchxlv:
    # These methods calculate the y and x level differences of the pinch gesture by comparing the
    # coordinates of landmark 8 (tip of the index finger) to the starting coordinates of the pinch.
    def getpinchylv(hand_result):
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y)*10,1)
        return dist

    def getpinchxlv(hand_result):
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord)*10,1)
        return dist
    
    # changesystemvolume:
    # This method adjusts the system volume based on the pinch level calculated from the pinch gesture.
    def changesystemvolume():
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()
        currentVolumeLv += Controller.pinchlv/50.0
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)

    
    # get_position:
    # This method calculates the cursor position based on the hand_result, specifically landmark 9
    # (between index finger and thumb). It stabilizes the cursor using dampening techniques by
    # taking into account the previous cursor position and distance traveled.
    def get_position(hand_result):
        point = 9
        position = [hand_result.landmark[point].x ,hand_result.landmark[point].y]
        sx,sy = pyautogui.size()
        x_old,y_old = pyautogui.position()
        x = int(position[0]*sx)
        y = int(position[1]*sy)
        if Controller.prev_hand is None:
            Controller.prev_hand = x,y
        delta_x = x - Controller.prev_hand[0]
        delta_y = y - Controller.prev_hand[1]

        distsq = delta_x**2 + delta_y**2
        ratio = 1
        Controller.prev_hand = [x,y]

        if distsq <= 25:
            ratio = 0
        elif distsq <= 900:
            ratio = 0.07 * (distsq ** (1/2))
        else:
            ratio = 2.1
        x , y = x_old + delta_x*ratio , y_old + delta_y*ratio
        return (x,y)

    # pinch_control_init:
    # This method initializes the pinch control by setting starting x and y coordinates, pinch level,
    # previous pinch level, and frame count.
    def pinch_control_init(hand_result):
        Controller.pinchstartxcoord = hand_result.landmark[8].x
        Controller.pinchstartycoord = hand_result.landmark[8].y
        Controller.pinchlv = 0
        Controller.prevpinchlv = 0
        Controller.framecount = 0

    
    # pinch_control:
    # This method handles pinch control actions, which can be either vertical or horizontal based on
    # the detected hand gesture. It maintains a frame count for consistent pinch gestures.
    def pinch_control(hand_result, controlVertical):
        if Controller.framecount == 5:
            Controller.framecount = 0
            Controller.pinchlv = Controller.prevpinchlv
            
            if Controller.pinchdirectionflag == False:
                controlVertical() #y

        lvx =  Controller.getpinchxlv(hand_result)
        lvy =  Controller.getpinchylv(hand_result)
            
        if abs(lvy) > abs(lvx) and abs(lvy) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = False
            if abs(Controller.prevpinchlv - lvy) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvy
                Controller.framecount = 0

        elif abs(lvx) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = True
            if abs(Controller.prevpinchlv - lvx) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvx
                Controller.framecount = 0

    @classmethod
    def handle_drag(cls, hand_result):
        x, y = cls.get_position(hand_result)
        if not cls.grabflag:
            cls.grabflag = True
            pyautogui.mouseDown(button="left")
        pyautogui.moveTo(x, y, duration=0.1)

    @classmethod
    def handle_left_click(cls, hand_result):
        if cls.flag:
            pyautogui.click()
            cls.flag = False

    @classmethod
    def handle_right_click(cls, hand_result):
        if cls.flag:
            pyautogui.click(button='right')
            cls.flag = False

    @classmethod
    def handle_double_click(cls, hand_result):
        if cls.flag:
            pyautogui.doubleClick()
            cls.flag = False

    @classmethod
    def handle_scroll(cls, hand_result):
        # Extract the index finger and thumb landmarks
        thumb_tip = hand_result.landmark[cls.THUMB_TIP]
        index_tip = hand_result.landmark[cls.INDEX_TIP]

        # Calculate the distance between the thumb and index finger
        distance = math.sqrt((thumb_tip.x - index_tip.x)**2 + (thumb_tip.y - index_tip.y)**2)

        # Define a threshold for the pinch gesture
        pinch_threshold = 0.03

        if distance < pinch_threshold:
            # Calculate the vertical movement of the hand
            hand_movement = hand_result.landmark[cls.WRIST].y - hand_result.landmark[cls.MIDDLE_TIP].y
            scroll_amount = int(hand_movement * 500)
            pyautogui.scroll(scroll_amount)


    @classmethod
    def handle_system_volume(cls, hand_result):
        if cls.pinchmajorflag == False:
            cls.pinch_control_init(hand_result)
            cls.pinchmajorflag = True
        cls.pinch_control(hand_result, cls.changesystemvolume)

    @classmethod
    def handle_palm(cls, hand_result):
        pass  # Placeholder for "PALM" gesture, you can add the code for the desired action here

    @classmethod
    def move_mouse(cls, hand_result):
        cls.flag = True
        x, y = cls.get_position(hand_result)
        pyautogui.moveTo(x, y, duration = 0.1)    

    # read_mappings: 
    # This method reads the gesture mappings from a 'mappings.txt' file and converts it to a dictionary.
    @classmethod
    def read_mappings(cls):
        with open('mappings.txt', 'r') as f:
            lines = f.readlines()

        mappings = {}
        for line in lines:
            if line.strip():
                gesture, action = line.strip().split(':')
                mappings[gesture] = action
        return mappings

    
    # execute_action:
    # This method takes a gesture name as input and executes the corresponding action method based on the gesture mappings.
    @classmethod
    def execute_action(cls, gesture_name, hand_result):
        mappings = cls.read_mappings()
        action_name = mappings.get(gesture_name)
        
        if action_name is not None:
            action_method = getattr(cls, action_name, None)
            if action_method is not None:
                action_method(hand_result)
            else:
                print(f"Error: {action_name} method not found in Controller class.")
        else:
            print(f"Error: Gesture {gesture_name} not found in mappings.")
    
    # handle_controls:
    # This method executes different actions based on the detected hand gestures, such as moving the
    # cursor, clicking, double-clicking, scrolling, and changing system volume. The actions are
    # performed using the PyAutoGUI library and involve calculations based on hand landmarks.
     # handle_controls:
    # This method has been updated to use the execute_action method to execute the appropriate action for a given gesture.
    @classmethod
    def handle_controls(cls, gesture, hand_result):
        if gesture.name is not None:
             # Check if the binary encoding of the gesture is in the allowed set
            allowed_encodings = {0, 1, 2, 4, 7, 8, 12, 15, 16, 31, 33, 34, 35, 36}
            #print(gesture.name)
            if gesture.binary_encoding in allowed_encodings:
                if gesture == Gest.PINCH_MINOR:
                    if cls.pinchminorflag == False:
                        cls.pinch_control_init(hand_result)
                        cls.pinchminorflag = True
                    #cls.pinch_control(hand_result, cls.scrollHorizontal, cls.scrollVertical)
                    cls.handle_scroll(hand_result)
                elif gesture == Gest.PINCH_MAJOR:
                    if cls.pinchmajorflag == False:
                        cls.pinch_control_init(hand_result)
                        cls.pinchmajorflag = True
                    cls.pinch_control(hand_result, cls.changesystemvolume)
                else:

                    gesture_name = gesture.name
                    cls.pinchmajorflag=False
                    cls.pinchminorflag=False
                    cls.execute_action(gesture_name, hand_result)
            else:
                print(f"Gesture {gesture.name} with binary encoding {gesture.binary_encoding} is not allowed.")
      
'''
----------------------------------------  Main Class  ----------------------------------------
    Entry point of Gesture Controller
'''

# GestureController class methods:
# --------------------------------
class GestureController:
    gc_mode = 0
    cap = None
    CAM_HEIGHT = None
    CAM_WIDTH = None
    hr_major = None  # Right Hand by default
    hr_minor = None  # Left hand by default
    dom_hand = True

    # __init__:
    # Initializes the GestureController object by setting the mode, capturing video from the default
    # camera, and retrieving the camera's frame height and width.
    def __init__(self):
        GestureController.gc_mode = 1
        GestureController.cap = cv2.VideoCapture(0)
        GestureController.CAM_HEIGHT = GestureController.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        GestureController.CAM_WIDTH = GestureController.cap.get(cv2.CAP_PROP_FRAME_WIDTH)

    # classify_hands:
    # This static method classifies the detected hands as left or right, and updates the hr_major and
    # hr_minor attributes based on the handedness.
    @staticmethod
    def classify_hands(results):
        left, right = None, None
        try:
            handedness_dict = MessageToDict(results.multi_handedness[0])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]
            else:
                left = results.multi_hand_landmarks[0]
        except:
            pass

        try:
            handedness_dict = MessageToDict(results.multi_handedness[1])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]
            else:
                left = results.multi_hand_landmarks[1]
        except:
            pass

        if GestureController.dom_hand == True:
            GestureController.hr_major = right
            GestureController.hr_minor = left
        else:
            GestureController.hr_major = left
            GestureController.hr_minor = right

    # process_frame:
    # This method processes a video frame, detects hand landmarks, updates the HandRecog objects for
    # major and minor hands, and calls the handle_controls method of the Controller class to perform
    # actions based on the detected gestures. The processed frame with hand landmarks is returned.
    def process_frame(self, frame, gesture_detection_active):
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)

        with mp_hands.Hands(max_num_hands = 2,min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
            while GestureController.cap.isOpened() and GestureController.gc_mode:
                gesture_detection_active.wait()  
               
                #applying resizing to speed up the image processing
                frame = cv2.resize(frame, (100, 100))

                #Apply a Gaussian blur to the input frame to reduce noise and improve hand detection.
                #frame = cv2.GaussianBlur(frame, (5, 5), 0)

                #Background subtraction: to separate the hand from the background, 
                # making it easier to detect and track the hand. 
                #This method is the MOG2 background subtractor.
                fgbg = cv2.createBackgroundSubtractorMOG2()
                fgmask = fgbg.apply(frame)

                #Morphological operations: Apply morphological operations, 
                #such as dilation and erosion, to clean up the binary image 
                #resulting from background subtraction or other segmentation methods.
                kernel = np.ones((5, 5), np.uint8)
                dilation = cv2.dilate(fgmask, kernel, iterations=1)
                erosion = cv2.erode(dilation, kernel, iterations=1)
                frame = erosion    

                success, image = self.cap.read()

                if not success:
                    print("Ignoring empty camera frame.")
                    continue
                
                image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                image.flags.writeable = False
                results = hands.process(image)
                
                image.flags.writeable = True
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                if results.multi_hand_landmarks:                   
                    GestureController.classify_hands(results)
                    handmajor.update_hand_result(GestureController.hr_major)
                    handminor.update_hand_result(GestureController.hr_minor)

                    handmajor.set_finger_state()
                    handminor.set_finger_state()
                    gest_name = handminor.get_gesture()

                    if gest_name == Gest.PINCH_MINOR:
                        Controller.handle_controls(Gest(gest_name), handminor.hand_result)
                    else:
                        gest_name = handmajor.get_gesture()
                        Controller.handle_controls(Gest(gest_name), handmajor.hand_result)
                    
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                else:
                    Controller.prev_hand = None
                
                if cv2.waitKey(5) & 0xFF == 13:
                    break
        
                # Return the annotated image.
        return image