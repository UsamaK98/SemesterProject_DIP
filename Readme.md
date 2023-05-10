# Gesture Controlled Virtual Mouse

This project aims to implement a gesture-controlled virtual mouse using OpenCV, Mediapipe, PyAutoGUI, and other essential Python libraries. This software leverages real-time hand gesture recognition using Mediapipe hands to detect hands' motion and position.

## Main Features

- Recognizes hand gestures from camera input.
- Maps gestures to specific functions such as controlling mouse movements, clicks, right-clicks or double-clicks, making sound, and scrolling up/down or right/left.
- Provides options for custom mappings of gestures.
- Works with multi-hand input by detecting the predominant hand.
- Uses Mediapipe's pose estimation to localize hand and finger landmarks and track their movement.
- Applies dampening to stabilize mouse movements.
- Incorporates a pinch control mechanism for vertical scrolling [Disabled] or adjusting the system volume.
- Background color change option using hand gestures (thumbs up -> black & thumbs down -> white). [Disabled]
- Integrates with PyAudio to adjust sound levels based on pinch input. 

### Optional Features - (To be added)

- Display the detected gesture label as text on the screen or a small overlay.
- Add more gestures to control other functionalities.
- Add a menu or setting to select the dominant hand and other options.
- Add audio feedback for different gestures, to indicate successful detection.

## Requirements

- Python 3.x
- OpenCV
- Mediapipe
- PyAutoGUI
- Flask
- PyAudio (optional)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/gesture-controlled-virtual-mouse.git
```

2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
   
```bash
flask run
```

2. Open your browser and navigate to http://localhost:5000 to view the live video feed and interact with the application.

3. Perform hand gestures to control the virtual mouse.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
MIT
