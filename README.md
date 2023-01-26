# Fuse Downloaded Combo Bags into one Rosbag

`DLR Holoscene` and `DLR SDP` platforms record sensor data into a ZIP file.
Use this repository to convert it into a single rosbag for further analysis and visualization.

## Quickstart

Clone this repository:

```
git clone https://github.com/borealbikes-dev/combo-rosbag-fuser.git
```

Install [Docker](https://docs.docker.com/engine/install/) for your system.

Move/copy the ZIP file obtained from the Boreal Web Interface into `input` directory.

Then run the script:

```
./run_fuser.sh
```

See `output` directory for a new `.mcap` rosbag.

Use [Foxglove](https://foxglove.dev/) to view its contents.

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
