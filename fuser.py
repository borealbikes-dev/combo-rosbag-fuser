# fuse.py 
# Read an mcap rosbag and mp4 files, then combine them into a new mcap rosbag
#
# Run this script from within a Docker container which has ROS2 Galactic and mcap plugin installed. See Dockerfile.galactic for the Dockerfile.
import argparse
import time
import os
import sys
import glob 
import multiprocessing
import yaml
import shutil

from tqdm import tqdm

from rclpy.serialization import serialize_message, deserialize_message
import rosbag2_py
from rosidl_runtime_py.utilities import get_message

from sensor_msgs.msg import Image
from sensor_msgs.msg import CompressedImage

import cv2
import numpy as np

# debugging
WORK_FROM_INTERMEDIATE = False

def form_compressed_image_msg(frame, encode_param):
    msg = CompressedImage()
    msg.format = "jpeg"
    msg.data.frombytes(cv2.imencode('.jpg', frame, encode_param)[1])
    return msg

def form_image_msg(frame):
    msg = Image()
    msg.height = frame.shape[0]
    msg.width = frame.shape[1]
    msg.encoding = "bgr8"
    msg.is_bigendian = 0
    msg.step = frame.shape[1] * 3

    flattened = np.ravel(frame)
    msg.data.frombytes(flattened)
    return msg

def parse_start_time_from_filename(filename):
    try:
        # filename format:path/to/file/csi-1673684144607-ms-001-minutes.mp4
        split_filename = filename.split('/')[-1].split('-')
        camera_type = split_filename[0]
        start_time_ms = int(split_filename[1])
        minutes_elapsed = int(split_filename[3])
    except ValueError:
        print("ERROR: Unable to parse start time from filename. Please check video filename format example: csi-1673684144607-ms-001-minutes.mp4")
        sys.exit(0)
    return start_time_ms

def write_video_to_bag(writer, mp4_files, topic_name, args, pbar):
    if not len(mp4_files):
        return

    if not args.raw:
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), args.jpeg_quality]
    message_type = "sensor_msgs/msg/CompressedImage" if not args.raw else "sensor_msgs/msg/Image"
    writer.create_topic(
        rosbag2_py.TopicMetadata(
            name=topic_name,
            type=message_type,
            serialization_format="cdr",
        )
    )

    start_time_nanos = int(parse_start_time_from_filename(mp4_files[0]) * 1e6)

    elapsed_frames = 0
    written_frames = 0

    for i, video_file in enumerate(mp4_files):
        elapsed_frames = 0
        cap = cv2.VideoCapture(video_file)

        num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fps = int(cap.get(cv2.CAP_PROP_FPS))

        framerate = cap.get(cv2.CAP_PROP_FPS)
        frame_time_nanos = 1_000_000_000 // int(framerate)

        while(cap.isOpened()):
            if args.skip_frames > 0:
                for _ in range(args.skip_frames):
                    ret, frame = cap.read()
                    elapsed_frames += 1
                    pbar.update(1)
                    if not ret:
                        break

            ret, frame = cap.read()

            if ret:
                if args.target_resolution != 'None':
                    if frame.shape[0] < args.target_resolution[0] or frame.shape[1] < args.target_resolution[1]:
                        print("WARNING: Target resolution is larger than frame resolution. Please check --target-resolution argument.")
                    
                if args.target_resolution != 'None':
                    frame = cv2.resize(frame, (args.target_resolution[1], args.target_resolution[0]), interpolation=cv2.INTER_AREA)

                if args.raw:
                    msg = form_image_msg(frame)
                else:
                    msg = form_compressed_image_msg(frame, encode_param)

                timestamp = start_time_nanos + written_frames* frame_time_nanos + int(args.video_timestamp_offset * 1e6)

                writer.write(topic_name, serialize_message(msg), timestamp)

                elapsed_frames += 1
                written_frames += 1
                pbar.update(1)
            else:
                break

def fuse(combo_bag_dir, args, pbar_frames, pbar_messages):
    '''
    Combo bag is structured as follows:

    combo_bag_2023-01-25_17-03-15/ # absolute path: combo_bag_dir
    ├── camera
    │   └── usb2 # a directory for each camera source
    │       ├── usb-1674662595562-ms-000-minutes.mp4  # filename contains start of video for this camera in milliseconds (since linux epoch)
    │       └── usb-1674662595562-ms-001-minutes.mp4  # files are split by 1 minute when recording 
    └── rosbag
        ├── metadata.yaml
        ├── rosbag_0.mcap # rosbag for first minute
        └── rosbag_1.mcap # rosbag for second minute 
    '''


    combo_bag_name = combo_bag_dir.split("/")[-1]

    # create a bag
    writer = rosbag2_py.SequentialWriter()
    writer.open(
        rosbag2_py.StorageOptions(uri=os.path.join(args.output_dir, combo_bag_name), storage_id="mcap"),
        rosbag2_py.ConverterOptions(
            input_serialization_format="cdr",
            output_serialization_format="cdr",
        ),
    )

    mp4_dirs = glob.glob(combo_bag_dir + "/camera/*")
    for mp4_dir in mp4_dirs:
        mp4_files = sorted(glob.glob(mp4_dir + "/*.mp4"))
        camera_name = mp4_dir.split("/")[-1]
        camera_topic_name = "/image/" + camera_name
        write_video_to_bag(writer, mp4_files, camera_topic_name , args, pbar_frames)

    rosbag_dir = os.path.join(combo_bag_dir, "rosbag")
    bag_splits = glob.glob(rosbag_dir + "/*.mcap")

    for i, bag_file in enumerate(bag_splits):
        reader = rosbag2_py.SequentialReader()
        reader.open(
            rosbag2_py.StorageOptions(uri=bag_file, storage_id="mcap"),
            rosbag2_py.ConverterOptions(
                input_serialization_format="cdr",
                output_serialization_format="cdr",
            ),
        )

        topics = []

        topic_types = reader.get_all_topics_and_types()

        while reader.has_next():
            topic, msg, timestamp = reader.read_next()
            if topic not in topics:
                topics.append(topic)
                writer.create_topic(
                    rosbag2_py.TopicMetadata(
                        name=topic,
                        type=typename(topic, topic_types),
                        serialization_format="cdr",
                    )
                )
            #print("Reading from bag, timestap: ", timestamp, " topic: ", topic)
            writer.write(topic, msg, timestamp)
            pbar_messages.update()
    
    del writer

def get_frame_count(video_file):
    cap = cv2.VideoCapture(video_file)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return frame_count

def main(args):
    working_dir = os.path.join(args.output_dir, "intermediate")

    if not WORK_FROM_INTERMEDIATE:
        zip_files = glob.glob(args.input_dir+ "/*.zip")
        with tqdm(zip_files, desc="Step 1: Unzipping", total=len(zip_files), unit='archives') as pbar_zip_parent:
            for zip_file in pbar_zip_parent:
                shutil.unpack_archive(zip_file, working_dir)

    # for tqdm total
    total_frames = 0
    for combo_bag in glob.glob(working_dir + "/*"):
        for mp4_dir in glob.glob(combo_bag + "/camera/*"):
            for mp4_file in glob.glob(mp4_dir + "/*.mp4"):
                total_frames += get_frame_count(mp4_file)
    total_messages = 0
    for combo_bag in glob.glob(working_dir + "/*"):
        yaml_metadata_file = os.path.join(combo_bag, "rosbag", "metadata.yaml")
        with open(yaml_metadata_file, "r") as f:
            metadata = yaml.load(f, Loader=yaml.FullLoader)
            total_messages += metadata['rosbag2_bagfile_information']['message_count']
    
    # work on each unzipped combo bag directory:
    with tqdm(total=total_frames, desc="Step 2: Fusing Images", unit="frames") as pbar_frames:
        with tqdm(total=total_messages, desc="Step 3: Fusing Messages", unit="messages") as pbar_messages:
            for combo_bag_dir in glob.glob(working_dir + "/*"):
                fuse(combo_bag_dir, args, pbar_frames, pbar_messages)
    
    print(f"\nDone! Find your fused bag at {args.output_dir}\n")

def typename(topic_name, topic_types):
        for topic_type in topic_types:
            if topic_type.name == topic_name:
                return topic_type.type
        raise ValueError(f"topic {topic_name} not in bag")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='fuse.py')
    parser.add_argument('--input-dir', help='path to directory containing zipped combo files downloaded from holoscene bike', default='/input')
    parser.add_argument('--output-dir', help='path to output directory', default='/output')
    parser.add_argument('--raw', help='do not use jpeg compression', action='store_true', default=False)
    parser.add_argument('--jpeg-quality', help='jpeg compression quality. Disregarded if --raw flag is set', type=int, default=75)
    parser.add_argument('--skip-frames', help="Skip video frames to speed up fusing and reduce space", type=int, default=0)
    parser.add_argument('--target-resolution', help='target resolution for output bag. Each frame is resized to [width]x[height]. Reduce to fuse faster.', type=str, default='None')
    parser.add_argument('--video-timestamp-offset', help='offset in milliseconds to add to video timestamps. Depending on your system, there can be a ~1000ms difference between when the mp4 file is created (named) and the actual first frame. Measure it by taking a video of the system clock in ms and comparing it to the file name.', type=int, default=1000)

    args = parser.parse_args()

    if args.target_resolution != 'None':
        split_res = args.target_resolution.split('x')
        args.target_resolution = [
            int(split_res[1]),
            int(split_res[0]),
        ]

    if args.raw:
        print("WARNING: (--raw) Raw images results in much larger files and slower processing. Use JPEG (ROS CompressedImage) unless you have a good reason not to.")
    
    # make sure input directory is not empty
    if len(os.listdir(args.input_dir)) == 0:
        print(f"Input directory {args.input_dir} is empty. Please place your zipped combo files in this directory before running.")
        os.makedirs(args.input_dir, exist_ok=True)
        exit(1)

    if os.path.exists(args.output_dir):
        if len(os.listdir(args.output_dir)) > 0:
            print(f"Output directory {args.output_dir} is not empty. Please delete the contents before running.")
            exit(1)
    os.makedirs(args.output_dir, exist_ok=True)


    main(args)
