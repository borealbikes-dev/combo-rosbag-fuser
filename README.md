# Fuse Downloaded Combo Bags into one Rosbag

`DLR Holoscene` and `DLR SDP` platforms record sensor data into a ZIP file.
Use this repository to convert it into a single rosbag for further analysis and visualization.

## Quickstart

Install [Docker] for your system.

Move/copy the ZIP file obtained from the Boreal Web Interface into `input` directory.

Then run the script:

```
./run_fuser.sh
```

The script will write an `.mcap` rosbag to the `output` directory.
By default, the name will be the same as the zip file.
Please see the references and example below for more options.

## Anatomy of combo_bag

An unzipped combo_bag looks something like this:
```
combo_bag_2023-01-25_17-03-15/  # date format: YYYY-MM-DD_HH-MM-SS
├── camera
│   └── usb2 # a directory for each camera source
│       ├── usb-1674662595562-ms-000-minutes.mp4  # filename contains start of video for this camera in milliseconds (since linux epoch)
│       └── usb-1674662595562-ms-001-minutes.mp4  # files are split by 1 minute when recording 
└── rosbag
    ├── metadata.yaml
    ├── rosbag_0.mcap # rosbag for first minute
    └── rosbag_1.mcap # rosbag for second minute 
```

### Post-facto Fusion

```
./run_docker_for_fuser.sh
```

In the created shell with ROS2 activated, run:

```
python3 fuser.py
```

This will create a new single rosbag file in `output/` directory which contains both the video and the ROS topics.

There are several options for `fuser.py` to help reduce storage, for example. Run `python3 fuser.py --help` to see them.

## Todo
- [ ] Desktop Dockerfile for ROS2 for faster fusing. (Currently only works on Jetson)
- [ ] May 2023: ROS2 Iron release with MCAP as default. Removes need for customized Dockerfile.
